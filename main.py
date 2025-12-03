# -*- coding: utf-8 -*-
import logging
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import asyncio

API_TOKEN = '8395187432:AAGlx0H3cVr16-ResTU9RX5RoNLJLaG50As'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()  # пустой Dispatcher
router = Router()

# ----- Города Луганской области -----
LUHANSK_CITIES = [
    "Луганск", "Алчевск", "Антрацит", "Брянка", "Кировск", "Красный Луч", "Краснодон",
    "Лисичанск", "Перевальск", "Первомайск", "Ровеньки", "Северодонецк", "Стаханов", "Свердловск",
    "Снежное", "Лутугино", "Молодогвардейск", "Счастье", "Новоайдар", "Славяносербск",
    "Троицкое", "Попасная", "Каменнобродский", "Приволье"
]

# ----- Категории и подкатегории -----
CATEGORIES = {
    "Ремонт": ["Бытовая техника","Газовое оборудование","Сантехника","Электрика","Мелкий ремонт дома",
               "Ремонт окон/дверей","Ремонт мебели","Компьютерная/IT помощь"],
    "Уборка": ["Дом/квартира","Офис","Послестройная уборка","Химчистка ковров и мебели",
               "Мытьё окон","Уборка территории"],
    "Авто": ["Такси","Шиномонтаж","Ремонт авто","Автомойка","Эвакуатор","Аренда авто","Доставка грузов"],
    "Строительство": ["Ремонт квартир","Отделка","Фасады","Ландшафтный дизайн","Сантехнические работы",
                      "Электромонтажные работы"],
    "Красота и здоровье": ["Парикмахерские услуги","Маникюр/Педикюр","Массаж","Кератиновое выпрямление",
                           "Лазерная эпиляция","Косметология","Спа-процедуры","Фитнес и тренировки"],
    "Доставка / Курьеры": ["Продукты","Посылки","Документы","Курьер на час","Локальная доставка"],
    "Обучение / Репетиторы": ["Школьные предметы","Языки","Онлайн-курсы","Музыкальные уроки","Танцы и спорт"],
    "Разное / Прочие услуги": ["Фото и видеосъёмка","Организация праздников","Риелторские услуги",
                               "Юридическая помощь","Консалтинг","Психолог / коучинг"]
}

# ----- База данных -----
users_db = {}       # user_id: {name, contact}
services_db = []    # {service_id, user_id, city, category, subcategory, description, photos, rating, reviews, active, active_until}
reviews_db = []     # {service_id, user_id, score, text}

# ----- Состояния пользователя -----
user_states = {}    # user_id: {"step":..., "data": {...}, "photos": []}

# ----- Главное меню -----
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Разместить услугу 💼", callback_data="place_service"),
        InlineKeyboardButton("Найти услугу 🔍", callback_data="find_service")
    )
    kb.add(
        InlineKeyboardButton("Мои услуги 📋", callback_data="my_services"),
        InlineKeyboardButton("Отзывы и рейтинг ⭐", callback_data="reviews")
    )
    kb.add(
        InlineKeyboardButton("Помощь / Информация ℹ️", callback_data="help")
    )
    return kb

# ----- Меню города -----
def city_menu(prefix):
    kb = InlineKeyboardMarkup(row_width=2)
    for city in LUHANSK_CITIES:
        kb.add(InlineKeyboardButton(city, callback_data=f"{prefix}_{city}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
    return kb

# ----- Меню категории -----
def category_menu(prefix):
    kb = InlineKeyboardMarkup(row_width=2)
    for cat in CATEGORIES.keys():
        kb.add(InlineKeyboardButton(cat, callback_data=f"{prefix}_{cat}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="city_back"))
    return kb

# ----- Меню подкатегории -----
def subcategory_menu(category, prefix):
    kb = InlineKeyboardMarkup(row_width=2)
    for subcat in CATEGORIES[category]:
        kb.add(InlineKeyboardButton(subcat, callback_data=f"{prefix}_{subcat}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="category_back"))
    return kb

# ----- Меню оплаты -----
def payment_menu(service_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("Я оплатил ✅", callback_data=f"paid_{service_id}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
    return kb

# ----- Меню Мои услуги -----
def my_services_menu(user_id):
    kb = InlineKeyboardMarkup(row_width=1)
    user_services = [s for s in services_db if s['user_id']==user_id]
    if not user_services:
        kb.add(InlineKeyboardButton("У вас пока нет услуг", callback_data="none"))
    else:
        for s in user_services:
            status = "✅ Активна" if s['active'] else "❌ Неактивна"
            title = f"{s['subcategory']} ({s['city']}) - {status} - Рейтинг: {s['rating']}/5"
            kb.add(InlineKeyboardButton(title, callback_data=f"service_{s['service_id']}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="main_menu"))
    return kb

# ----- Старт -----
@router.message(Command("start"))
async def start(message: types.Message):
    users_db[message.from_user.id] = {"name": message.from_user.full_name, "contact": ""}
    await message.answer("Добро пожаловать в VoznekoZone!\nВыберите действие:", reply_markup=main_menu())

# ----- Callback обработка -----
@router.callback_query(lambda c: True)
async def callbacks(call: types.CallbackQuery):
    data = call.data
    user_id = call.from_user.id

    if data == "main_menu":
        await call.message.edit_text("Главное меню:", reply_markup=main_menu())

    elif data == "place_service":
        user_states[user_id] = {"step": "choose_city", "data": {}, "photos": []}
        await call.message.edit_text("Выберите город для размещения услуги:", reply_markup=city_menu("place"))

    elif data == "find_service":
        user_states[user_id] = {"step": "search_city", "data": {}}
        await call.message.edit_text("Выберите город для поиска услуги:", reply_markup=city_menu("find"))

    elif data.startswith("place_") and data != "place_service":
        city = data.replace("place_", "")
        user_states[user_id]["data"]["city"] = city
        user_states[user_id]["step"] = "choose_category"
        await call.message.edit_text(f"Город выбран: {city}\nВыберите категорию:", reply_markup=category_menu("place"))

    elif data.startswith("find_") and data != "find_service":
        city = data.replace("find_", "")
        user_states[user_id]["data"]["city"] = city
        user_states[user_id]["step"] = "search_category"
        await call.message.edit_text(f"Город выбран: {city}\nВыберите категорию для поиска:", reply_markup=category_menu("find"))

    elif data == "my_services":
        await call.message.edit_text("Ваши услуги:", reply_markup=my_services_menu(user_id))

# ----- Обработка текста -----
@router.message()
async def text_handler(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {})

    if state.get("step") == "enter_description":
        desc = message.text
        user_states[user_id]["data"]["description"] = desc
        service_id = len(services_db) + 1
        new_service = {
            "service_id": service_id,
            "user_id": user_id,
            "city": state["data"]["city"],
            "category": state["data"]["category"],
            "subcategory": state["data"]["subcategory"],
            "description": desc,
            "photos": state["photos"],
            "rating": 0,
            "reviews": [],
            "active": False,
            "active_until": None
        }
        services_db.append(new_service)
        await message.answer(f"Услуга создана: {desc}\nНажмите «Я оплатил» для активации услуги.", reply_markup=payment_menu(service_id))
        user_states.pop(user_id)

# ----- Проверка подписки каждый день -----
async def check_subscriptions():
    while True:
        now = datetime.now()
        for s in services_db:
            if s['active'] and s['active_until'] and s['active_until'] < now:
                s['active'] = False
                await bot.send_message(s['user_id'], f"Подписка на услугу '{s['subcategory']}' завершена. Продлите её для повторной активности.")
        await asyncio.sleep(86400)  # раз в сутки

# ----- Подключаем router -----
dp.include_router(router)

# ----- Запуск бота -----
if __name__ == "__main__":
    async def main():
        asyncio.create_task(check_subscriptions())
        await dp.start_polling(bot)
    asyncio.run(main())
