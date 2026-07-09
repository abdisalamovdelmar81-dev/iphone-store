from pathlib import Path

import pytest

from iphone_bot.db import StoreDB


@pytest.mark.asyncio
async def test_cart_and_order_flow(tmp_path: Path) -> None:
    db = StoreDB(tmp_path / "store.sqlite3")
    await db.init()
    try:
        products = await db.get_products(query="iphone")
        assert products

        product_id = products[0]["id"]
        ok, _ = await db.add_to_cart(user_id=1001, product_id=product_id)
        assert ok

        cart = await db.get_cart(user_id=1001)
        assert len(cart) == 1
        assert cart[0].cart_quantity == 1

        order_id, total, items = await db.create_order(
            user_id=1001,
            username="client",
            full_name="Test Client",
            address="Москва, улица Тестовая, дом 1",
        )
        assert order_id > 0
        assert total == items[0].price
        assert await db.get_cart(user_id=1001) == []
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_search_by_color(tmp_path: Path) -> None:
    db = StoreDB(tmp_path / "store.sqlite3")
    await db.init()
    try:
        products = await db.get_products(query="розовый")
        assert len(products) == 1
        assert products[0]["color"] == "Розовый"
    finally:
        await db.close()
