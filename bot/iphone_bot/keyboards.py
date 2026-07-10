from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu(is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="Каталог"), KeyboardButton(text="Корзина")],
        [KeyboardButton(text="Мой ID")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="Добавить товар")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def catalog_keyboard(products) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=product["name"],
            callback_data=f"product:{product['id']}",
        )
    builder.button(text="Корзина", callback_data="cart")
    builder.adjust(1)
    return builder.as_markup()


def product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить в корзину", callback_data=f"add_cart:{product_id}")
    builder.button(text="Каталог", callback_data="catalog")
    builder.button(text="Корзина", callback_data="cart")
    builder.adjust(1)
    return builder.as_markup()


def cart_keyboard(has_items: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_items:
        builder.button(text="Заказать", callback_data="checkout")
        builder.button(text="Очистить корзину", callback_data="clear_cart")
    builder.button(text="Каталог", callback_data="catalog")
    builder.adjust(1)
    return builder.as_markup()
