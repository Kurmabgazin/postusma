import asyncio
import re
import logging
import uuid
import pandas as pd
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ContentType
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
)
from aiogram.filters import CommandStart, Command

API_TOKEN = '7796410844:AAGeLfSf2tXWB-yk0Gte_UxaCCF5px7ajNs'
OWNER_ID = 434772555  # замените на ваш Telegram ID

logging.basicConfig(level=logging.INFO)

orders = []

def normalize_phone(phone: str) -> str:
    return re.sub(r'\D', '', phone)

def normalize_text(text: str) -> str:
    return text.strip().lower()

def load_orders_from_file(file_path: str):
    global orders
    try:
        df = pd.read_excel(file_path)
        orders.clear()
        for _, row in df.iterrows():
            phone = normalize_phone(str(row.get("Телефон", "")))
            fio = str(row.get("ФИО", "")).strip()
            track = str(row.get("Трек", "")).strip()
            date = str(row.get("Дата отправки", "")).strip()
            if phone or fio:
                orders.append({
                    "phone": phone,
                    "fio": fio,
                    "track": track,
                    "date": date
                })
        logging.info(f"Загружено {len(orders)} заказов из файла {file_path}")
        return True, f"Файл успешно загружен. Найдено заказов: {len(orders)}"
    except Exception as e:
        logging.error(f"Ошибка при загрузке заказов: {e}")
        return False, f"Ошибка при загрузке файла: {e}"

user_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Треки")],
        [KeyboardButton(text="Инфо")],
        [KeyboardButton(text="Скидки")]
    ],
    resize_keyboard=True
)

phone_request_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отправить номер телефона", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Загрузить заказы")],
        [KeyboardButton(text="Посмотреть количество заказов")],
        [KeyboardButton(text="Выйти из админки")]
    ],
    resize_keyboard=True
)

back_to_menu_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Главное меню")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

async def start_handler(message: Message):
    if message.from_user.id == OWNER_ID:
        await message.answer("Привет, админ! Вы в главном меню.", reply_markup=admin_menu)
    else:
        await message.answer("Добро пожаловать! Выберите действие.", reply_markup=user_menu)

async def help_handler(message: Message):
    await message.answer(
        "Это бот для отслеживания заказов.\n\n"
        "Команды:\n"
        "/start — главное меню\n"
        "Инфо — информация о нас\n"
        "Скидки — текущие акции\n"
        "Треки — поиск заказа по телефону или ФИО\n"
        "\nДля админа:\n"
        "Загрузить заказы — загрузить Excel-файл с заказами\n"
        "Посмотреть количество заказов — узнать количество загруженных заказов\n"
        "Выйти из админки — выйти в пользовательское меню"
    )

async def info_handler(message: Message):
    await message.answer(
        "Мы — бренд ухода за кожей с любовью ❤️\n\n"
        "📍 Работаем по Казахстану\n"
        "📦 Отправка 1–2 дня\n"
        "📱 По всем вопросам — пишите менеджеру"
    )

async def discount_handler(message: Message):
    await message.answer("🎉 Сейчас действует скидка 10% на второй товар в корзине!")

async def tracks_menu_handler(message: Message):
    await message.answer(
        "Пожалуйста, отправьте номер телефона или ФИО, либо выберите кнопку ниже:",
        reply_markup=phone_request_kb
    )

async def handle_contact(message: Message):
    phone = normalize_phone(message.contact.phone_number)
    await send_order_info(phone, message)

async def send_order_info(query: str, message: Message):
    normalized_phone = normalize_phone(query)
    normalized_fio = normalize_text(query)

    found_orders = []
    for order in orders:
        if normalized_phone and order["phone"] == normalized_phone:
            found_orders.append(order)
        elif normalized_fio and normalize_text(order["fio"]) == normalized_fio:
            found_orders.append(order)

    if found_orders:
        response = ""
        for idx, order in enumerate(found_orders, start=1):
            response += (
                f"Заказ #{idx}:\n"
                f"📦 Трек-номер: {order['track']}\n"
                f"👤 ФИО: {order['fio']}\n"
                f"📅 Дата отправки: {order['date']}\n\n"
            )
        await message.answer(response.strip())
    else:
        await message.answer("❌ Заказ не найден. Проверьте номер телефона или ФИО и попробуйте снова.")

async def handle_document(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только администратор может загружать файлы.")
        return

    document = message.document
    if not document.file_name.endswith(('.xlsx', '.xls')):
        await message.answer("❌ Пожалуйста, загрузите Excel-файл (.xlsx или .xls)")
        return

    file_path = f"temp_{uuid.uuid4()}.xlsx"
    file = await message.bot.download(document, destination=file_path)

    success, msg = load_orders_from_file(file_path)
    await message.answer(msg)

async def handle_admin_commands(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Эта команда только для админа.")
        return

    text = message.text.strip().lower()
    if text == "загрузить заказы":
        await message.answer("Отправьте Excel-файл с заказами (.xlsx или .xls).")
    elif text == "посмотреть количество заказов":
        await message.answer(f"В базе сейчас {len(orders)} заказов.")
    elif text == "выйти из админки":
        await message.answer("Вы вышли из админ-панели.", reply_markup=user_menu)
    else:
        await handle_text(message)

async def handle_text(message: Message):
    if message.from_user.id == OWNER_ID and message.text.strip().lower() in [
        "загрузить заказы", "посмотреть количество заказов", "выйти из админки"
    ]:
        await handle_admin_commands(message)
        return

    text = message.text.strip().lower()
    if text == "инфо":
        await info_handler(message)
    elif text == "скидки":
        await discount_handler(message)
    elif text == "треки":
        await tracks_menu_handler(message)
    elif text == "главное меню":
        if message.from_user.id == OWNER_ID:
            await message.answer("Вы в главном меню.", reply_markup=admin_menu)
        else:
            await message.answer("Вы в главном меню.", reply_markup=user_menu)
    else:
        await send_order_info(text, message)

async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    dp.message.register(start_handler, CommandStart())
    dp.message.register(help_handler, Command("help"))
    dp.message.register(handle_contact, F.content_type == ContentType.CONTACT)
    dp.message.register(handle_document, F.content_type == ContentType.DOCUMENT)
    dp.message.register(handle_text)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
