"""
Test entry handler - for entering test code and getting test link.
"""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.markdown import hbold

from states.registration import TestEntryStates
from keyboards.menu import get_main_menu, get_cancel_keyboard, get_remove_keyboard
from api_client import api_client
from config import settings


router = Router()


@router.message(TestEntryStates.waiting_for_test_code)
async def process_test_code(message: Message, state: FSMContext):
    """Process test code and create session."""
    test_code = message.text.strip().upper()
    
    try:
        # Get test from API
        test = await api_client.get_test_by_code(test_code)
        
        if not test:
            await message.answer(
                f"❌ '{test_code}' kodli test topilmadi yoki faol emas.\n\n"
                "Iltimos, kodni tekshirib qayta urinib ko'ring.",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        # Check time window
        from datetime import datetime, timedelta, timezone
        uz_tz = timezone(timedelta(hours=5))
        now = datetime.now(uz_tz).replace(tzinfo=None)  # UZ local time without timezone info
        
        if test.get('start_time'):
            start_str = test['start_time'].replace('Z', '').replace('+00:00', '')
            # Remove fractional seconds if present
            if '.' in start_str:
                start_str = start_str.split('.')[0]
            start_time = datetime.fromisoformat(start_str)
            if now < start_time:
                await message.answer(
                    f"⏰ <b>Test hali boshlanmadi!</b>\n\n"
                    f"Test boshlanish vaqti: {start_time.strftime('%d.%m.%Y %H:%M')}\n\n"
                    "O'sha vaqtda qayta urinib ko'ring.",
                    parse_mode="HTML",
                    reply_markup=get_main_menu()
                )
                await state.clear()
                return
        
        if test.get('end_time'):
            end_str = test['end_time'].replace('Z', '').replace('+00:00', '')
            if '.' in end_str:
                end_str = end_str.split('.')[0]
            end_time = datetime.fromisoformat(end_str)
            extra = test.get('extra_minutes', 0)
            effective_end = end_time + timedelta(minutes=extra)
            if now >= effective_end:
                await message.answer(
                    "❌ <b>Test vaqti tugagan!</b>\n\n"
                    "Bu testni ishlash uchun belgilangan vaqt tugadi.",
                    parse_mode="HTML",
                    reply_markup=get_main_menu()
                )
                await state.clear()
                return
        
        # Get user
        user = await api_client.get_user_by_telegram_id(message.from_user.id)
        
        # Create session
        session = await api_client.create_session(user['id'], test['id'])
        
        if session and session.get('payment_required'):
            # Pullik test, balans yetarli emas
            from handlers.payments import format_sum, show_payment_instructions
            info = session['payment_required']
            intro = (f"💰 <b>Bu test pullik:</b> {format_sum(info.get('price'))}\n"
                     f"📝 {test['title']} ({test['test_code']})\n"
                     f"💳 Balansingiz: {format_sum(info.get('balance'))}\n\n")
            if info.get('pending_amount', 0) >= info.get('required', 0):
                await state.clear()
                await message.answer(
                    intro + "⏳ Siz yuborgan chek tekshirilmoqda. Admin tasdiqlagach sizga xabar keladi, "
                    "shundan keyin test kodini qayta yuboring.",
                    parse_mode="HTML", reply_markup=get_main_menu())
                return
            intro += f"Testga kirish uchun balansingizni <b>{format_sum(info.get('required'))}</b> ga to'ldiring.\n\n"
            await show_payment_instructions(message, state, int(info.get('required') or 0), test=test, intro=intro)
            return

        if not session or session.get('error'):
            error_msg = session.get('error', '') if session else ''
            
            if 'not started' in error_msg.lower() or 'boshlanmadi' in error_msg.lower():
                await message.answer(
                    "⏰ <b>Test hali boshlanmadi!</b>\n\n"
                    "Test boshlanish vaqtini kuting.",
                    parse_mode="HTML",
                    reply_markup=get_main_menu()
                )
            elif 'ended' in error_msg.lower() or 'tugagan' in error_msg.lower():
                await message.answer(
                    "❌ <b>Test vaqti tugagan!</b>\n\n"
                    "Bu testni ishlash uchun belgilangan vaqt tugadi.",
                    parse_mode="HTML",
                    reply_markup=get_main_menu()
                )
            elif 'already' in error_msg.lower() or 'attempted' in error_msg.lower():
                await message.answer(
                    "❌ Siz bu testni allaqachon topshirgansiz!\n\n"
                    "Har bir talaba testni faqat bir marta ishlashi mumkin.",
                    reply_markup=get_main_menu()
                )
            else:
                await message.answer(
                    f"❌ Sessiya yaratishda xatolik: {error_msg}\n\n"
                    "Iltimos, qayta urinib ko'ring.",
                    reply_markup=get_main_menu()
                )
            await state.clear()
            return
        
        # Calculate remaining time display
        if test.get('end_time'):
            end_str = test['end_time'].replace('Z', '').replace('+00:00', '')
            if '.' in end_str:
                end_str = end_str.split('.')[0]
            end_time = datetime.fromisoformat(end_str)
            extra = test.get('extra_minutes', 0)
            effective_end = end_time + timedelta(minutes=extra)
            remaining_minutes = max(0, int((effective_end - now).total_seconds() / 60))
            hours = remaining_minutes // 60
            mins = remaining_minutes % 60
            time_str = f"{hours} soat {mins} daqiqa" if hours > 0 else f"{mins} daqiqa"
        else:
            time_str = "1 soat 30 daqiqa"
        
        # Generate test link
        test_url = f"{settings.WEB_APP_URL}/static/student/index.html?token={session['session_token']}"
        
        # Build message text
        msg_text = (
            f"✅ <b>Test topildi!</b>\n\n"
            f"📝 {test['title']}\n"
            + (f"💰 Narxi: {int(test['price']):,} so'm (balansdan yechildi)\n".replace(",", " ") if test.get('price') else "")
            + f"⏱️ Qolgan vaqt: {time_str}\n"
            f"📊 Savollar:\n"
            f"   • Test (1-35): 1-32 savollarda 4 ta, 33-35 savollarda 6 ta variant\n"
            f"   • Yozma (36-45): Har bir savolda a) va b) qismlari bor\n\n"
            f"⚠️ <b>Muhim:</b>\n"
            f"• Havolani ochganingizda taymer boshlanadi\n"
            f"• Testni to'xtatib bo'lmaydi\n"
            f"• Vaqt tugaganda avtomatik topshiriladi\n"
            f"• Faqat bir urinish!\n\n"
            f"Omad tilaymiz! 🍀"
        )
        
        await state.clear()
        
        # Build inline keyboard with test link + main menu
        if "localhost" in test_url or "127.0.0.1" in test_url:
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="main_menu")]
            ])
            await message.answer(
                msg_text + f"\n\n<b>🔗 Testni boshlash:</b>\n{test_url}",
                parse_mode="HTML",
                reply_markup=inline_kb,
                disable_web_page_preview=True
            )
        else:
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Testni boshlash", web_app=WebAppInfo(url=test_url))],
                [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="main_menu")]
            ])
            await message.answer(
                msg_text,
                parse_mode="HTML",
                reply_markup=inline_kb
            )
        
    except Exception as e:
        await message.answer(
            f"❌ Xatolik: {str(e)}\n\n"
            "Iltimos, qayta urinib ko'ring yoki yordam uchun murojaat qiling.",
            reply_markup=get_main_menu()
        )
        await state.clear()
