"""
Keyboard menus for the bot - all inline keyboards.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove


def get_main_menu() -> InlineKeyboardMarkup:
    """Get main menu as inline keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Testni boshlash", callback_data="start_test")],
        [
            InlineKeyboardButton(text="📊 Natijalarim", callback_data="my_results"),
            InlineKeyboardButton(text="💳 Balans", callback_data="balance")
        ],
        [InlineKeyboardButton(text="📈 Test tahlili", callback_data="test_analytics")],
    ])


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Get cancel keyboard as inline button for FSM flows."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])


def get_remove_keyboard() -> ReplyKeyboardRemove:
    """Remove any existing reply keyboard."""
    return ReplyKeyboardRemove()
