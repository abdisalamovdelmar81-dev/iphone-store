from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


@dataclass(frozen=True)
class CartLine:
    product_id: int
    name: str
    color: str
    quantity: int
    cart_quantity: int
    price: int

    @property
    def subtotal(self) -> int:
        return self.price * self.cart_quantity


class StoreDB:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self._create_schema()
        await self._seed_products()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    @property
    def db(self) -> aiosqlite.Connection:
        if self.conn is None:
            raise RuntimeError("Database is not initialized.")
        return self.conn

    async def _create_schema(self) -> None:
        await self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity >= 0),
                price INTEGER NOT NULL CHECK(price >= 0),
                color TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cart_items (
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                PRIMARY KEY (user_id, product_id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                address TEXT NOT NULL,
                total INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_items (
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_name TEXT NOT NULL,
                color TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price INTEGER NOT NULL
            );
            """
        )
        await self._ensure_product_images_column()
        await self.db.commit()

    async def _ensure_product_images_column(self) -> None:
        cursor = await self.db.execute("PRAGMA table_info(products)")
        columns = {row["name"] for row in await cursor.fetchall()}
        if "image_url" not in columns:
            await self.db.execute("ALTER TABLE products ADD COLUMN image_url TEXT NOT NULL DEFAULT ''")

    async def _seed_products(self) -> None:
        cursor = await self.db.execute("SELECT COUNT(*) AS count FROM products")
        row = await cursor.fetchone()
        if row and row["count"]:
            await self._fill_missing_product_images()
            return

        products = [
            ("iPhone 16 Pro Max 256 ГБ", 5, 139990, "Натуральный титан", image_url_for_name("iPhone 16 Pro Max 256 ГБ")),
            ("iPhone 16 Pro 256 ГБ", 7, 119990, "Пустынный титан", image_url_for_name("iPhone 16 Pro 256 ГБ")),
            ("iPhone 16 128 ГБ", 10, 84990, "Ультрамарин", image_url_for_name("iPhone 16 128 ГБ")),
            ("iPhone 15 Pro Max 256 ГБ", 4, 119990, "Синий титан", image_url_for_name("iPhone 15 Pro Max 256 ГБ")),
            ("iPhone 15 128 ГБ", 12, 72990, "Розовый", image_url_for_name("iPhone 15 128 ГБ")),
            ("iPhone 14 128 ГБ", 8, 61990, "Голубой", image_url_for_name("iPhone 14 128 ГБ")),
            ("iPhone 13 128 ГБ", 6, 54990, "Тёмная ночь", image_url_for_name("iPhone 13 128 ГБ")),
        ]
        now = utc_now()
        await self.db.executemany(
            "INSERT INTO products(name, quantity, price, color, image_url, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [(name, qty, price, color, image_url, now) for name, qty, price, color, image_url in products],
        )
        await self.db.commit()

    async def _fill_missing_product_images(self) -> None:
        cursor = await self.db.execute("SELECT id, name, image_url FROM products")
        rows = await cursor.fetchall()
        updates = [
            (image_url_for_name(row["name"]), row["id"])
            for row in rows
            if not row["image_url"] and image_url_for_name(row["name"])
        ]
        if updates:
            await self.db.executemany("UPDATE products SET image_url = ? WHERE id = ?", updates)
            await self.db.commit()

    async def add_product(self, name: str, quantity: int, price: int, color: str = "", image_url: str = "") -> int:
        cursor = await self.db.execute(
            "INSERT INTO products(name, quantity, price, color, image_url, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name.strip(), quantity, price, color.strip(), image_url.strip(), utc_now()),
        )
        await self.db.commit()
        return int(cursor.lastrowid)

    async def get_product(self, product_id: int) -> aiosqlite.Row | None:
        cursor = await self.db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        return await cursor.fetchone()

    async def get_products(self, query: str | None = None, only_available: bool = True) -> list[aiosqlite.Row]:
        cursor = await self.db.execute("SELECT * FROM products ORDER BY id DESC")
        rows = await cursor.fetchall()
        if only_available:
            rows = [row for row in rows if row["quantity"] > 0]
        if query:
            needle = query.casefold().strip()
            rows = [
                row
                for row in rows
                if needle in row["name"].casefold() or needle in row["color"].casefold()
            ]
        return rows

    async def add_to_cart(self, user_id: int, product_id: int) -> tuple[bool, str]:
        product = await self.get_product(product_id)
        if product is None:
            return False, "Товар не найден."
        if product["quantity"] <= 0:
            return False, "Этого товара сейчас нет в наличии."

        cursor = await self.db.execute(
            "SELECT quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        )
        row = await cursor.fetchone()
        current = int(row["quantity"]) if row else 0
        if current >= product["quantity"]:
            return False, "Больше нет в наличии."

        if row:
            await self.db.execute(
                "UPDATE cart_items SET quantity = quantity + 1 WHERE user_id = ? AND product_id = ?",
                (user_id, product_id),
            )
        else:
            await self.db.execute(
                "INSERT INTO cart_items(user_id, product_id, quantity) VALUES (?, ?, 1)",
                (user_id, product_id),
            )
        await self.db.commit()
        return True, "Товар добавлен в корзину."

    async def get_cart(self, user_id: int) -> list[CartLine]:
        cursor = await self.db.execute(
            """
            SELECT p.id, p.name, p.color, p.quantity, p.price, c.quantity AS cart_quantity
            FROM cart_items c
            JOIN products p ON p.id = c.product_id
            WHERE c.user_id = ?
            ORDER BY p.name
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            CartLine(
                product_id=row["id"],
                name=row["name"],
                color=row["color"],
                quantity=row["quantity"],
                cart_quantity=row["cart_quantity"],
                price=row["price"],
            )
            for row in rows
        ]

    async def clear_cart(self, user_id: int) -> None:
        await self.db.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        await self.db.commit()

    async def create_order(
        self,
        user_id: int,
        username: str | None,
        full_name: str,
        address: str,
    ) -> tuple[int, int, list[CartLine]]:
        items = await self.get_cart(user_id)
        if not items:
            raise ValueError("cart_is_empty")

        not_enough = [item for item in items if item.cart_quantity > item.quantity]
        if not_enough:
            names = ", ".join(item.name for item in not_enough)
            raise ValueError(f"not_enough:{names}")

        total = sum(item.subtotal for item in items)
        await self.db.execute("BEGIN IMMEDIATE")
        try:
            cursor = await self.db.execute(
                """
                INSERT INTO orders(user_id, username, full_name, address, total, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, full_name, address.strip(), total, utc_now()),
            )
            order_id = int(cursor.lastrowid)
            await self.db.executemany(
                "INSERT INTO order_items(order_id, product_name, color, quantity, price) VALUES (?, ?, ?, ?, ?)",
                [
                    (order_id, item.name, item.color, item.cart_quantity, item.price)
                    for item in items
                ],
            )
            await self.db.executemany(
                "UPDATE products SET quantity = quantity - ? WHERE id = ?",
                [(item.cart_quantity, item.product_id) for item in items],
            )
            await self.db.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
            await self.db.commit()
            return order_id, total, items
        except Exception:
            await self.db.rollback()
            raise


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def image_url_for_name(name: str) -> str:
    base = "https://raw.githubusercontent.com/abdisalamovdelmar81-dev/iphone-store/main/assets/products"
    lower = name.casefold()
    if "iphone 16 pro max" in lower:
        return f"{base}/iphone-16-pro-hero.jpg"
    if "iphone 16 pro" in lower:
        return f"{base}/iphone-16-pro.jpg"
    if "iphone 16" in lower:
        return f"{base}/iphone-16.jpg"
    if "iphone 15 pro" in lower:
        return f"{base}/iphone-15-pro.jpg"
    if "iphone 15" in lower:
        return f"{base}/iphone-15.jpg"
    if "iphone 14" in lower:
        return f"{base}/iphone-14.jpg"
    if "iphone 13" in lower:
        return f"{base}/iphone-13.jpg"
    return ""
