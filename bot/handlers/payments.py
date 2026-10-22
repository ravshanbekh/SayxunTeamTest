"""
Balans va to'lov: karta rekvizitlarini ko'rsatish, chekni (skrinshot yoki PDF) qabul qilish.
"""
import re
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from api_client import api_client
from keyboards.menu import get_cancel_keyboard, get_main_menu
from states.registration import PaymentStates

router = Router()

MIN_AMOUNT = 1_000
MAX_AMOUNT = 50_000_000
MAX_FILE_BYTES = 10 * 1024 * 1024


def format_sum(value) -> str:
    return f"{int(value or 0):,}".replace(",", " ") + " so'm"


def balance_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Balansni to'ldirish", callback_data="topup")],
        [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="main_menu")],
    ])


async def show_payment_instructions(message: Message, state: FSMContext, amount: int,
                                    test: Optional[dict] = None, intro: str = "") -> None:
    """Karta rekvizitlari va chek yuborish so'rovi. Holat: chek kutilmoqda."""
    info = await api_client.get_payment_info()
    card = (info.get("card_number") or "").strip()
    holder = (info.get("card_holder") or "").strip()
    note = (info.get("note") or "").strip()

    if not card:
        await state.clear()
        await message.answer(
            intro + "⚠️ To'lov rekvizitlari hali kiritilmagan. O'quv markazi administratoriga murojaat qiling.",
            parse_mode="HTML", reply_markup=get_main_menu())
        return

    text = intro
    text += (f"💳 <b>To'lov uchun karta:</b>\n"
             f"<code>{card}</code>\n")
    if holder:
        text += f"👤 {holder}\n"
    text += f"\n💵 To'lanadigan summa: <b>{format_sum(amount)}</b>\n"
    if note:
        text += f"ℹ️ {note}\n"
    text += ("\n📎 Pulni o'tkazgach, <b>chek skrinshotini</b> (rasm) yoki <b>PDF chekni</b> shu yerga yuboring.\n"
             "Admin tekshirib tasdiqlagach, balansingiz to'ldiriladi va sizga xabar keladi.")

    await state.set_state(PaymentStates.waiting_for_receipt)
    await state.update_data(pay_amount=amount, pay_test_id=(test or {}).get("id"),
                            pay_test_code=(test or {}).get("test_code"))
    await message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard())


@router.callback_query(F.data == "balance")
async def callback_balance(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    balance = await api_client.get_balance(callback.from_user.id)
    if balance is None:
        await callback.message.edit_text("❌ Avval ro'yxatdan o'ting: /start", reply_markup=get_main_menu())
        await callback.answer()
        return
    text = f"💰 <b>Balansingiz:</b> {format_sum(balance['balance'])}\n"
    if balance.get("pending_amount"):
        text += f"⏳ Tekshirilayotgan to'lovlar: {format_sum(balance['pending_amount'])}\n"
    text += "\nPullik testlarga kirishda test narxi balansdan yechiladi."
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=balance_keyboard())
    await callback.answer()


@router.callback_query(F.data == "topup")
async def callback_topup(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PaymentStates.waiting_for_amount)
    await callback.message.edit_text(
        "💵 <b>Qancha summa to'lamoqchisiz?</b>\n\nSummani so'mda yozing, masalan: <code>30000</code>",
        parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await callback.answer()


@router.message(PaymentStates.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    digits = re.sub(r"[^\d]", "", message.text or "")
    amount = int(digits) if digits else 0
    if not (MIN_AMOUNT <= amount <= MAX_AMOUNT):
        await message.answer(
            f"❌ Summani raqam bilan yozing ({format_sum(MIN_AMOUNT)} dan {format_sum(MAX_AMOUNT)} gacha).",
            reply_markup=get_cancel_keyboard())
        return
    await show_payment_instructions(message, state, amount)


@router.message(PaymentStates.waiting_for_receipt, F.photo | F.document)
async def process_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("pay_amount")
    if not amount:
        await state.clear()
        await message.answer("❌ Xatolik. Qaytadan urinib ko'ring.", reply_markup=get_main_menu())
        return

    if message.photo:
        photo = message.photo[-1]
        file_id, filename, content_type, size = photo.file_id, "chek.jpg", "image/jpeg", photo.file_size
    else:
        doc = message.document
        mime = (doc.mime_type or "").lower()
        if mime != "application/pdf" and not mime.startswith("image/"):
            await message.answer("❌ Chek rasm yoki PDF bo'lishi kerak.", reply_markup=get_cancel_keyboard())
            return
        file_id, filename, content_type, size = doc.file_id, doc.file_name or "chek", mime, doc.file_size

    if size and size > MAX_FILE_BYTES:
        await message.answer("❌ Fayl juda katta (maksimal 10 MB).", reply_markup=get_cancel_keyboard())
        return

    buffer = await message.bot.download(file_id)
    result = await api_client.submit_payment(
        message.from_user.id, int(amount), buffer.getvalue(), filename, content_type,
        test_id=data.get("pay_test_id"))
    if result.get("error"):
        await message.answer(f"❌ {result['error']}", reply_markup=get_cancel_keyboard())
        return

    await state.clear()
    text = (f"✅ <b>Chek qabul qilindi!</b>\n\n"
            f"💵 Summa: {format_sum(amount)}\n"
            f"⏳ Admin tekshirib tasdiqlagach, balansingiz to'ldiriladi va sizga xabar keladi.")
    if data.get("pay_test_code"):
        text += f"\n\n📝 Tasdiqlangandan keyin <b>{data['pay_test_code']}</b> test kodini qayta yuboring."
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_menu())


@router.message(PaymentStates.waiting_for_receipt)
async def receipt_expected(message: Message):
    await message.answer(
        "📎 Iltimos, to'lov chekining <b>skrinshotini</b> (rasm) yoki <b>PDF</b> faylini yuboring.",
        parse_mode="HTML", reply_markup=get_cancel_keyboard())
