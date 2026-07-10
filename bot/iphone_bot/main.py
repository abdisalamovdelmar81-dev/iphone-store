from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .config import Config, load_config
from .db import CartLine, StoreDB
from .keyboards import catalog_keyboard, cart_keyboard, main_menu, product_keyboard


class AddProductFlow(StatesGroup):
    name = State()
    quantity = State()
    price = State()


class OrderFlow(StatesGroup):
    address = State()


def money(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " ₽"


def is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


def user_full_name(message: Message) -> str:
    parts = [message.from_user.first_name if message.from_user else ""]
    if message.from_user and message.from_user.last_name:
        parts.append(message.from_user.last_name)
    return " ".join(part for part in parts if part).strip() or "Клиент"


def product_text(product) -> str:
    return (
        f"{product['name']}\n"
        f"Цена: {money(product['price'])}\n"
        f"В наличии: {product['quantity']} шт."
    )


def cart_text(items: list[CartLine]) -> str:
    if not items:
        return "Корзина пустая. Открой каталог и добавь iPhone."

    lines = ["Твоя корзина:"]
    total = 0
    for item in items:
        total += item.subtotal
        lines.append(
            f"- {item.name}: {item.cart_quantity} шт. x {money(item.price)} = {money(item.subtotal)}"
        )
    lines.append(f"\nИтого: {money(total)}")
    return "\n".join(lines)


def order_admin_text(
    order_id: int,
    total: int,
    items: list[CartLine],
    message: Message,
    address: str,
) -> str:
    username = f"@{message.from_user.username}" if message.from_user and message.from_user.username else "без username"
    lines = [
        f"Новый заказ #{order_id}",
        f"Клиент: {user_full_name(message)} ({username})",
        f"ID клиента: {message.from_user.id if message.from_user else 'неизвестно'}",
        f"Адрес: {address}",
        "",
        "Товары:",
    ]
    for item in items:
        lines.append(f"- {item.name}: {item.cart_quantity} шт. x {money(item.price)}")
    lines.append(f"\nИтого: {money(total)}")
    return "\n".join(lines)


async def send_catalog(target: Message, db: StoreDB, query: str | None = None) -> None:
    products = await db.get_products(query=query)
    if not products:
        await target.answer("Ничего не нашёл. Попробуй другое имя или цвет.")
        return

    title = "Каталог iPhone"
    if query:
        title = f"Результаты поиска: {query}"
    await target.answer(title, reply_markup=catalog_keyboard(products))


async def show_cart_message(target: Message, db: StoreDB, user_id: int) -> None:
    items = await db.get_cart(user_id)
    await target.answer(cart_text(items), reply_markup=cart_keyboard(bool(items)))


def setup_router(db: StoreDB, config: Config) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        await state.clear()
        admin = is_admin(message.from_user.id, config) if message.from_user else False
        await message.answer(
            "Привет! Это бот магазина iPhone. Выбери действие снизу.",
            reply_markup=main_menu(admin),
        )

    @router.message(Command("id"))
    @router.message(F.text == "Мой ID")
    async def my_id(message: Message) -> None:
        admin_note = ""
        if message.from_user and is_admin(message.from_user.id, config):
            admin_note = "\nТы уже админ в этом боте."
        await message.answer(f"Твой Telegram ID: {message.from_user.id}{admin_note}")

    @router.message(Command("catalog"))
    @router.message(F.text == "Каталог")
    async def catalog(message: Message, state: FSMContext) -> None:
        await state.clear()
        await send_catalog(message, db)

    @router.message(Command("cart"))
    @router.message(F.text == "Корзина")
    async def cart(message: Message, state: FSMContext) -> None:
        await state.clear()
        await show_cart_message(message, db, message.from_user.id)

    @router.callback_query(F.data == "catalog")
    async def catalog_callback(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await send_catalog(callback.message, db)

    @router.callback_query(F.data.startswith("product:"))
    async def product_callback(callback: CallbackQuery) -> None:
        await callback.answer()
        product_id = int(callback.data.split(":", 1)[1])
        product = await db.get_product(product_id)
        if product is None:
            if callback.message:
                await callback.message.answer("Товар не найден.")
            return
        if callback.message:
            await callback.message.answer(product_text(product), reply_markup=product_keyboard(product_id))

    @router.callback_query(F.data.startswith("add_cart:"))
    async def add_cart_callback(callback: CallbackQuery) -> None:
        product_id = int(callback.data.split(":", 1)[1])
        ok, text = await db.add_to_cart(callback.from_user.id, product_id)
        await callback.answer(text, show_alert=not ok)
        if callback.message:
            await callback.message.answer(text)

    @router.callback_query(F.data == "cart")
    async def cart_callback(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.message:
            await show_cart_message(callback.message, db, callback.from_user.id)

    @router.callback_query(F.data == "clear_cart")
    async def clear_cart_callback(callback: CallbackQuery) -> None:
        await db.clear_cart(callback.from_user.id)
        await callback.answer("Корзина очищена.")
        if callback.message:
            await callback.message.answer("Корзина очищена.", reply_markup=cart_keyboard(False))

    @router.callback_query(F.data == "checkout")
    async def checkout_callback(callback: CallbackQuery, state: FSMContext) -> None:
        items = await db.get_cart(callback.from_user.id)
        if not items:
            await callback.answer("Корзина пустая.", show_alert=True)
            return
        await callback.answer()
        await state.set_state(OrderFlow.address)
        if callback.message:
            await callback.message.answer("Напиши адрес доставки одним сообщением.")

    @router.message(OrderFlow.address)
    async def order_address(message: Message, state: FSMContext, bot: Bot) -> None:
        address = (message.text or "").strip()
        if len(address) < 8:
            await message.answer("Адрес слишком короткий. Напиши город, улицу, дом и квартиру.")
            return

        username = message.from_user.username if message.from_user else None
        try:
            order_id, total, items = await db.create_order(
                user_id=message.from_user.id,
                username=username,
                full_name=user_full_name(message),
                address=address,
            )
        except ValueError as error:
            await state.clear()
            text = str(error)
            if text.startswith("not_enough:"):
                await message.answer(f"Не хватает товара на складе: {text.removeprefix('not_enough:')}")
            else:
                await message.answer("Корзина пустая. Добавь товар из каталога.")
            return
        await state.clear()
        await message.answer(f"Заказ #{order_id} принят. Скоро с тобой свяжутся.\nИтого: {money(total)}")

        if not config.admin_ids:
            logging.warning("Order %s was created, but ADMIN_IDS is empty.", order_id)
            return
        text = order_admin_text(order_id, total, items, message, address)
        for admin_id in config.admin_ids:
            try:
                await bot.send_message(admin_id, text)
            except Exception:
                logging.exception("Could not send order %s to admin %s", order_id, admin_id)

    @router.message(Command("add"))
    async def add_command(message: Message, command: CommandObject, state: FSMContext) -> None:
        if not message.from_user or not is_admin(message.from_user.id, config):
            await message.answer("Эта команда только для админа.")
            return

        args = (command.args or "").strip()
        if args:
            try:
                name, qty, price = [part.strip() for part in args.split("|")]
                product_id = await db.add_product(name, int(qty), int(price))
            except ValueError:
                await message.answer("Формат: `/add iPhone 16 | 5 | 84990`", parse_mode="Markdown")
                return
            await message.answer(f"Товар добавлен. ID: {product_id}")
            return

        await state.set_state(AddProductFlow.name)
        await message.answer("Напиши имя товара. Например: iPhone 16 Pro 256 ГБ")

    @router.message(F.text.func(lambda text: text.casefold() == "добавить"))
    @router.message(F.text == "Добавить товар")
    async def add_text(message: Message, state: FSMContext) -> None:
        if not message.from_user or not is_admin(message.from_user.id, config):
            await message.answer("Эта команда только для админа.")
            return
        await state.set_state(AddProductFlow.name)
        await message.answer("Напиши имя товара. Например: iPhone 16 Pro 256 ГБ")

    @router.message(AddProductFlow.name)
    async def add_name(message: Message, state: FSMContext) -> None:
        name = (message.text or "").strip()
        if len(name) < 3:
            await message.answer("Имя слишком короткое. Напиши нормальное название товара.")
            return
        await state.update_data(name=name)
        await state.set_state(AddProductFlow.quantity)
        await message.answer("Сколько штук в наличии?")

    @router.message(AddProductFlow.quantity)
    async def add_quantity(message: Message, state: FSMContext) -> None:
        try:
            quantity = int((message.text or "").strip())
        except ValueError:
            await message.answer("Напиши количество цифрой, например: 5")
            return
        if quantity < 0:
            await message.answer("Количество не может быть меньше 0.")
            return
        await state.update_data(quantity=quantity)
        await state.set_state(AddProductFlow.price)
        await message.answer("Напиши цену в рублях цифрой. Например: 84990")

    @router.message(AddProductFlow.price)
    async def add_price(message: Message, state: FSMContext) -> None:
        try:
            price = int((message.text or "").replace(" ", "").strip())
        except ValueError:
            await message.answer("Напиши цену цифрой, например: 84990")
            return
        if price <= 0:
            await message.answer("Цена должна быть больше 0.")
            return
        data = await state.get_data()
        product_id = await db.add_product(
            name=data["name"],
            quantity=data["quantity"],
            price=price,
        )
        await state.clear()
        await message.answer(f"Готово, товар добавлен. ID: {product_id}")

    return router


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    db = StoreDB(config.db_path)
    await db.init()

    bot = Bot(token=config.bot_token)
    dp = Dispatcher()
    dp.include_router(setup_router(db, config))

    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
