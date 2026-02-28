"""
ConnectU Bot - To'liq qayta yozilgan versiya
"""

import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, WebAppInfo
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

# Konfiguratsiya
BOT_TOKEN = os.getenv("BOT_TOKEN", "8230210984:AAGld9gVSXps2zC22qyKH5gKXV946wdS2CM")
API_URL = os.getenv("MINI_APP_URL", "http://127.0.0.1:5000")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher(storage=MemoryStorage())

# ==================== FSM HOLATLAR ====================

class RegisterState(StatesGroup):
    role = State()              # Rol tanlash
    full_name = State()         # Ism familiya
    phone = State()             # Telefon raqam
    university = State()        # Universitet (faqat mentor uchun)
    faculty = State()           # Fakultet (faqat mentor uchun)
    year = State()              # Kurs (faqat mentor uchun)

# ==================== KEYBOARDS ====================

def role_keyboard():
    """Rol tanlash uchun inline keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Abituriyent", callback_data="role_student")],
        [InlineKeyboardButton(text="👨‍🏫 Mentor", callback_data="role_mentor")],
    ])

def phone_keyboard():
    """Telefon raqam yuborish uchun reply keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def main_menu_keyboard(role="student"):
    """Asosiy menyu"""
    if role == "mentor":
        buttons = [
            [KeyboardButton(text="📋 Profilim"), KeyboardButton(text="💰 Balans")],
            [KeyboardButton(text="📅 Sessiyalarim"), KeyboardButton(text="💬 Yordam")],
        ]
    else:
        buttons = [
            [KeyboardButton(text="🎓 Mentorlar"), KeyboardButton(text="🏫 Universitetlar")],
            [KeyboardButton(text="👤 Profilim"), KeyboardButton(text="💬 Yordam")],
        ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def webapp_keyboard(panel_url=None):
    """Mini App ochish uchun inline keyboard"""
    if not panel_url:
        panel_url = f"{API_URL}/login.html"
    
    # Telegram qoidasi: Web App URL faqat https bo'lishi shart!
    if panel_url.startswith("http://"):
        panel_url = panel_url.replace("http://", "https://")
    
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🚀 ConnectU ilovasini ochish",
            web_app=WebAppInfo(url=panel_url)
        )
    ]])

# ==================== API FUNKSIYALAR ====================

async def api_request(endpoint, method="GET", data=None):
    """Backend API ga so'rov yuborish"""
    url = f"{API_URL}{endpoint}"
    print(f"🔍 API so'rov: {url}")
    print(f"📦 Ma'lumot: {data}")
    
    try:
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url) as resp:
                    print(f"📥 Javob status: {resp.status}")
                    text = await resp.text()
                    print(f"📄 Javob matni (boshi): {text[:200]}")
                    
                    if text.strip().startswith('<!doctype') or text.strip().startswith('<html'):
                        print("❌ Server HTML qaytardi! Endpoint noto'g'ri")
                        return {"success": False, "error": "Server xatolik qaytardi"}
                    
                    try:
                        return await resp.json()
                    except:
                        return {"success": False, "error": f"JSON emas: {text[:100]}"}
            else:
                async with session.post(url, json=data) as resp:
                    print(f"📥 Javob status: {resp.status}")
                    text = await resp.text()
                    print(f"📄 Javob matni (boshi): {text[:200]}")
                    
                    if text.strip().startswith('<!doctype') or text.strip().startswith('<html'):
                        print("❌ Server HTML qaytardi! Endpoint noto'g'ri")
                        return {"success": False, "error": "Server xatolik qaytardi"}
                    
                    try:
                        return await resp.json()
                    except:
                        return {"success": False, "error": f"JSON emas: {text[:100]}"}
    except Exception as e:
        print(f"❌ API xatosi: {e}")
        return {"success": False, "error": str(e)}
        
# ==================== HANDLERS ====================

async def check_user_and_start(msg: types.Message, state: FSMContext):
    """Foydalanuvchini tekshirish va start qilish"""
    result = await api_request(f"/api/bot/user/{msg.from_user.id}")
    
    if result.get("success") and result.get("user"):
        user = result["user"]
        role = user.get("role", "student")
        name = user.get("full_name", "Foydalanuvchi")
        
        await msg.answer(
            f"👋 Xush kelibsiz, {name}!\n\n"
            f"ConnectU platformasiga xush kelibsiz.",
            reply_markup=main_menu_keyboard(role)
        )
        
        panel_url = get_panel_url(role)
        
        await msg.answer(
            "📲 Ilovani ochish:",
            reply_markup=webapp_keyboard(panel_url)
        )
    else:
        await msg.answer(
            "🎓 ConnectU ga xush kelibsiz!\n\n"
            "Iltimos, ro'lingizni tanlang:",
            reply_markup=role_keyboard()
        )
        await state.set_state(RegisterState.role)

@dp.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext):
    """Start komandasi - login va ro'yxatdan o'tish"""
    await state.clear()
    
    args = msg.text.split()
    if len(args) > 1:
        if args[1].startswith('dl_'):
            # Telegram tugmasi orqali - Tasdiq so'rash
            token = args[1].replace('dl_', '')
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_login_{token}")
            ]])
            await msg.answer(
                "🔐 <b>Tizimga kirish</b>\n\n"
                "Akkountingizga kirishni tasdiqlaysizmi?", 
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return
        elif args[1].startswith('qr_'):
            # QR kod orqali - To'g'ridan to'g'ri kirish
            token = args[1].replace('qr_', '')
            await process_login_token(msg, token, state)
            return
        elif args[1].startswith('login_'):
            # Ehtiyot shart uchun standart holat
            token = args[1].replace('login_', '')
            await process_login_token(msg, token, state)
            return
    
    # Oddiy start - foydalanuvchi borligini tekshirish
    user = await get_user_by_telegram_id(msg.from_user.id)
    
    if user:
        # Bor - asosiy menyu
        await show_main_menu(msg, user)
    else:
        # Yo'q - ro'yxatdan o'tish
        await show_registration_options(msg)

@dp.callback_query(F.data.startswith("confirm_login_"))
async def process_confirm_login(callback: types.CallbackQuery, state: FSMContext):
    """Telegram orqali kirishni tasdiqlashni qayta ishlash"""
    token = callback.data.replace("confirm_login_", "")
    await callback.message.delete()
    await process_login_token(callback.message, token, state, user=callback.from_user)
    await callback.answer()

@dp.callback_query(RegisterState.role, F.data.startswith("role_"))
async def process_role(callback: types.CallbackQuery, state: FSMContext):
    """Rol tanlashni qayta ishlash"""
    role = callback.data.replace("role_", "")
    await state.update_data(role=role)
    
    await callback.message.delete()
    
    if role == "mentor":
        await callback.message.answer(
            "👨‍🏫 Mentor ro'yxatdan o'tishi\n\n"
            "Ism va familiyangizni kiriting:"
        )
    else:
        await callback.message.answer(
            "🎓 Abituriyent ro'yxatdan o'tishi\n\n"
            "Ism va familiyangizni kiriting:"
        )
    
    await state.set_state(RegisterState.full_name)
    await callback.answer()

async def show_registration_options(msg: types.Message):
    """Ro'yxatdan o'tish variantlarini ko'rsatish"""
    # QR skanerlash tugmasi olib tashlandi
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎓 Abituriyent", callback_data="reg_student")],
        [InlineKeyboardButton(text="👨‍🏫 Mentor", callback_data="reg_mentor")]
    ])
    
    await msg.answer(
        "👋 <b>ConnectU ga xush kelibsiz!</b>\n\n"
        "Iltimos, ro'lingizni tanlang:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def show_main_menu(msg: types.Message, user: dict):
    """Asosiy menyuni ko'rsatish (Yetishmayotgan funksiya qo'shildi)"""
    role = user.get("role", "student")
    name = user.get("full_name", "Foydalanuvchi")
    
    await msg.answer(
        f"👋 Xush kelibsiz, {name}!\n\n"
        f"ConnectU platformasiga xush kelibsiz.",
        reply_markup=main_menu_keyboard(role)
    )
    
    panel_url = get_panel_url(role)
    
    await msg.answer(
        "📲 Ilovani ochish:",
        reply_markup=webapp_keyboard(panel_url)
    )

async def get_user_by_telegram_id(telegram_id):
    """Telegram ID orqali foydalanuvchini olish"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/api/bot/user/{telegram_id}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('user')
    except:
        pass
    return None
    
@dp.message(RegisterState.full_name)
async def process_full_name(msg: types.Message, state: FSMContext):
    """Ism familiyani qayta ishlash"""
    full_name = msg.text.strip()
    
    if len(full_name) < 3:
        await msg.answer("❌ Ism kamida 3 harf bo'lishi kerak. Qayta kiriting:")
        return
    
    await state.update_data(full_name=full_name)
    data = await state.get_data()
    
    if data.get("role") == "mentor":
        await msg.answer(
            "🏛 Qaysi universitetda o'qiysiz?\n"
            "Masalan: Toshkent Davlat Yuridik Universiteti"
        )
        await state.set_state(RegisterState.university)
    else:
        await msg.answer(
            "📱 Telefon raqamingizni yuboring:",
            reply_markup=phone_keyboard()
        )
        await state.set_state(RegisterState.phone)

@dp.message(RegisterState.university)
async def process_university(msg: types.Message, state: FSMContext):
    """Universitetni qayta ishlash"""
    university = msg.text.strip()
    await state.update_data(university=university)
    
    await msg.answer(
        "📚 Fakultetingizni kiriting:\n"
        "Masalan: Huquqshunoslik"
    )
    await state.set_state(RegisterState.faculty)

@dp.message(RegisterState.faculty)
async def process_faculty(msg: types.Message, state: FSMContext):
    """Fakultetni qayta ishlash"""
    faculty = msg.text.strip()
    await state.update_data(faculty=faculty)
    
    await msg.answer(
        "📅 Nechanchi kursdasiz?\n"
        "Masalan: 3"
    )
    await state.set_state(RegisterState.year)

@dp.message(RegisterState.year)
async def process_year(msg: types.Message, state: FSMContext):
    """Kursni qayta ishlash"""
    try:
        year = int(msg.text.strip())
        if year < 1 or year > 5:
            await msg.answer("❌ Kurs 1-5 oralig'ida bo'lishi kerak. Qayta kiriting:")
            return
    except ValueError:
        await msg.answer("❌ Noto'g'ri format. Raqam kiriting (masalan: 3):")
        return
    
    await state.update_data(year=year)
    
    await msg.answer(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard()
    )
    await state.set_state(RegisterState.phone)

@dp.message(RegisterState.phone, F.contact)
async def process_phone_contact(msg: types.Message, state: FSMContext):
    """Telefon raqamni kontakt orqali qayta ishlash"""
    phone = msg.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    
    await complete_registration(msg, state, phone)

@dp.message(RegisterState.phone)
async def process_phone_text(msg: types.Message, state: FSMContext):
    """Telefon raqamni matn orqali qayta ishlash"""
    phone = msg.text.strip().replace(" ", "").replace("-", "")
    
    if not phone.startswith("+998") or len(phone) < 13:
        await msg.answer(
            "❌ Noto'g'ri format. Telefon raqam +998901234567 formatida kiriting\n"
            "Yoki pastdagi tugmani bosing:",
            reply_markup=phone_keyboard()
        )
        return
    
    await complete_registration(msg, state, phone)

async def complete_registration(msg: types.Message, state: FSMContext, phone: str):
    """Ro'yxatdan o'tishni yakunlash"""
    data = await state.get_data()
    
    user_data = {
        "telegram_id": msg.from_user.id,
        "phone": phone,
        "full_name": data.get("full_name"),
        "username": msg.from_user.username or "",
        "role": data.get("role", "student")
    }
    
    if data.get("role") == "mentor":
        user_data["university"] = data.get("university")
        user_data["faculty"] = data.get("faculty")
        user_data["year"] = data.get("year")
    
    print(f"Ro'yxatdan o'tish: {user_data}")
    
    result = await api_request("/api/bot/register", "POST", user_data)
    print(f"Backend javobi: {result}")
    
    if result.get("success"):
        role = data.get("role", "student")
        name = data.get("full_name", "Foydalanuvchi")
        
        if role == "mentor":
            await msg.answer(
                "⚠️ MUHIM!\n\n"
                "Mentor paneliga kirgandan so'ng, 3 kun ichida\n"
                "talabalik guvohnomasini yuklashingiz kerak.\n"
                "Aks holda akkauntingiz o'chiriladi!"
            )
        
        role_label = "🎓 Abituriyent" if role == "student" else "👨‍🏫 Mentor"
        await msg.answer(
            f"✅ Tabriklaymiz, {name}!\n\n"
            f"Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.\n"
            f"Telefon raqamingiz: {phone}",
            reply_markup=main_menu_keyboard(role)
        )
        
        panel_url = get_panel_url(role)
        
        await msg.answer(
            "📲 Ilovani ochish:",
            reply_markup=webapp_keyboard(panel_url)
        )
    else:
        error_msg = result.get('error', "Noma'lum xatolik")
        await msg.answer(
            f"❌ Xatolik yuz berdi: {error_msg}\n\n"
            f"Qayta urinib ko'ring: /start"
        )
    
    await state.clear()

@dp.message(F.text == "👤 Profilim")
async def show_profile(msg: types.Message):
    """Profil ma'lumotlarini ko'rsatish"""
    result = await api_request(f"/api/bot/user/{msg.from_user.id}")
    
    if result.get("success") and result.get("user"):
        user = result["user"]
        
        role_text = "🎓 Abituriyent" if user.get("role") == "student" else "👨‍🏫 Mentor"
        
        text = "👤 Profilim\n\n"
        text += f"Ism: {user.get('full_name')}\n"
        text += f"Telefon: {user.get('phone')}\n"
        text += f"Rol: {role_text}\n"
        
        if user.get("role") == "mentor" and user.get("mentor_profile"):
            mp = user["mentor_profile"]
            text += "\nMentor ma'lumotlari:\n"
            text += f"Universitet: {mp.get('university')}\n"
            text += f"Fakultet: {mp.get('faculty')}\n"
            text += f"Kurs: {mp.get('year')}-kurs\n"
            
            status = "✅ Tasdiqlangan" if mp.get('is_verified') else "⏳ Kutilmoqda"
            text += f"Holat: {status}\n"
        
        await msg.answer(text)
    else:
        await msg.answer("❌ Profil topilmadi. /start ni bosing.")

@dp.message(F.text == "💬 Yordam")
async def help_handler(msg: types.Message):
    """Yordam xabari"""
    await msg.answer(
        "💬 Yordam\n\n"
        "📞 Admin: @connectu_admin\n"
        "🌐 Sayt: connectu.uz\n\n"
        "Agar muammo bo'lsa, admin bilan bog'lanishingiz mumkin."
    )

@dp.message(Command("cancel"))
async def cmd_cancel(msg: types.Message, state: FSMContext):
    """Amalni bekor qilish"""
    await state.clear()
    await msg.answer("❌ Bekor qilindi.", reply_markup=main_menu_keyboard())

@dp.message(F.text == "📱 Aktiv sessiyalar")
async def show_active_sessions(msg: types.Message):
    """Foydalanuvchining aktiv sessiyalarini ko'rsatish"""
    result = await api_request(f"/api/bot/user/{msg.from_user.id}")
    
    if not result.get('success'):
        await msg.answer("❌ Profil topilmadi")
        return
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/api/bot/sessions/{msg.from_user.id}") as resp:
            data = await resp.json()
            
            if not data.get('success'):
                await msg.answer("❌ Sessiyalarni olishda xatolik")
                return
            
            sessions = data.get('sessions', [])
            
            if not sessions:
                await msg.answer("📱 Hozircha aktiv sessiyalar yo'q.")
                return
            
            text = "📱 Aktiv sessiyalar\n\n"
            
            for i, s in enumerate(sessions, 1):
                device_info = s.get('device_info', {})
                device = device_info.get('device', 'Noma\'lum')
                browser = device_info.get('browser', '')
                os_name = device_info.get('os', '')
                ip = s.get('ip_address', 'Noma\'lum')
                time_str = s.get('logged_in_at', '').replace('T', ' ')[:16]
                
                text += f"{i}. {device}\n"
                if browser:
                    text += f"   Brauzer: {browser}\n"
                if os_name:
                    text += f"   OS: {os_name}\n"
                text += f"   IP: {ip}\n"
                text += f"   Kirish: {time_str}\n\n"
            
            if len(sessions) > 1:
                text += "Barcha sessiyalarni tugatish uchun: /logout_all"
            
            await msg.answer(text)

@dp.message(Command("logout_all"))
async def logout_all_sessions(msg: types.Message):
    """Barcha sessiyalarni tugatish"""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/api/bot/logout-all", json={
            'telegram_id': msg.from_user.id
        }) as resp:
            data = await resp.json()
            
            if data.get('success'):
                await msg.answer(
                    "✅ Barcha sessiyalar tugatildi!\n\n"
                    "Endi faqat shu qurilmadagi sessiya aktiv."
                )
            else:
                await msg.answer("❌ Xatolik yuz berdi.")

async def process_login_token(msg: types.Message, token: str, state: FSMContext, user: types.User = None):
    """Login tokenini qayta ishlash (QR/Deeplink)"""
    if user is None:
        user = msg.from_user
        
    waiting_msg = await msg.answer("🔄 Kirish tekshirilmoqda...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Backendga so'rov
            async with session.post(f"{API_URL}/api/bot/verify-login", json={
                'token': token,
                'telegram_id': user.id,
                'username': user.username or '',
                'first_name': user.first_name,
                'last_name': user.last_name
            }) as resp:
                
                if resp.status != 200:
                    await waiting_msg.edit_text("❌ Server bilan bog'lanib bo'lmadi")
                    return
                
                result = await resp.json()
                
                if result.get('success'):
                    user_data = result.get('user', {})
                    full_name = user_data.get('full_name', 'Foydalanuvchi')
                    role = user_data.get('role', 'student')
                    
                    # Muvaffaqiyatli login
                    success_text = (
                        f"✅ <b>Muvaffaqiyatli login!</b>\n\n"
                        f"🎉 <b>AKKAUNTINGIZGA KIRILDI</b>\n\n"
                        f"Xush kelibsiz, {full_name}!\n"
                        f"Rolingiz: {'🎓 Abituriyent' if role == 'student' else '👨‍🏫 Mentor'}"
                    )
                    await waiting_msg.edit_text(success_text, parse_mode="HTML")
                    
                    # Rolga qarab panel URL
                    if role == 'mentor':
                        panel_url = f"{API_URL}/mentor.html"
                    elif role in ['admin', 'superadmin']:
                        panel_url = f"{API_URL}/admin.html"
                    else:
                        panel_url = f"{API_URL}/abuturyent.html"
                    
                    # WebApp tugmasi bilan keyboard
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="🚀 Ilovani ochish",
                            web_app=WebAppInfo(url=panel_url.replace("http://", "https://"))
                        )
                    ]])
                    
                    await msg.answer(
                        "Ilovani ochish uchun tugmani bosing:",
                        reply_markup=keyboard
                    )
                    
                    # Eski sessiya haqida xabar
                    if result.get('session_replaced'):
                        device_info = result.get('old_session_device', {})
                        device_name = device_info.get('device', 'Noma\'lum')
                        ip_address = device_info.get('ip', 'Noma\'lum')
                        
                        await msg.answer(
                            f"⚠️ <b>Diqqat!</b>\n\n"
                            f"Boshqa qurilmada aktiv sessiya aniqlandi va to'xtatildi.\n"
                            f"Qurilma: {device_name}\n"
                            f"IP: {ip_address}",
                            parse_mode="HTML"
                        )
                else:
                    error_msg = result.get('error', 'Noma\'lum xatolik')
                    await waiting_msg.edit_text(
                        f"❌ <b>Login xatolik</b>\n\n{error_msg}",
                        parse_mode="HTML"
                    )
                    
    except Exception as e:
        await waiting_msg.edit_text(f"❌ Xatolik: {str(e)}")


def get_panel_url(role):
    """Rolga qarab panel URL qaytarish"""
    if role == 'mentor':
        return f"{API_URL}/mentor.html"
    elif role in ['admin', 'superadmin']:
        return f"{API_URL}/admin.html"
    else:
        return f"{API_URL}/abuturyent.html"

# ==================== MAIN ====================

async def main():
    log.info("🚀 ConnectU Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())