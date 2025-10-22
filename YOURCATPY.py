import os
import logging
import json
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from flask import Flask
from threading import Thread
import time

# === Flask сервер для поддержания активности ===
app = Flask('')

@app.route('/')
def home():
    return "🐱 Kitty City Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# === Настройка логирования ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Запускаем Flask сервер ===
keep_alive()

# === Токены ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8429919809:AAE5lMwVmH86X58JFDxYRPA3bDbFMgSgtsw")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5531546741"))

# === База данных в памяти (для бесплатного Replit) ===
users_db = {}
promocodes_db = {}
bot_stats = {
    "total_users": 0,
    "total_care_actions": 0,
    "start_time": datetime.now().isoformat()
}

# === Конфигурация ===
CAT_IMAGES = ["cat1.jpg", "cat2.jpg", "cat3.jpg", "cat4.jpg", "cat5.jpg"]

DEFAULT_USER_DATA = {
    "user_id": None,
    "username": "",
    "coins": 50,
    "rating": 0,
    "created_at": None,
    "cat": {
        "name": "Мурзик",
        "hunger": 5,
        "cleanliness": 5,
        "mood": 5,
        "health": 5,
        "last_update": None,
        "level": 1,
        "exp": 0,
        "care_count": 0,
        "photo_index": 0
    },
    "inventory": [],
    "tasks": {},
    "used_promocodes": [],
    "daily_care_count": 0,
    "last_care_date": None
}

CAT_NAME_OPTIONS = ["Барсик", "Мурзик", "Васька", "Рыжик", "Снежок", "Пушок", "Кузя"]

TOYS = {
    'i1': {'name': 'i1', 'price': 20, 'emoji': '🎾', 'display_name': 'Мячик'},
    'i2': {'name': 'i2', 'price': 30, 'emoji': '🐟', 'display_name': 'Рыбка'},
    'i3': {'name': 'i3', 'price': 40, 'emoji': '🎯', 'display_name': 'Мишень'},
}

BEDS = {
    'bed1': {'name': 'bed1', 'price': 150, 'emoji': '🛏️', 'display_name': 'Лежанка 1'},
    'bed2': {'name': 'bed2', 'price': 200, 'emoji': '🏠', 'display_name': 'Лежанка 2'},
}

# === Функции базы данных ===
def user_exists(user_id):
    return str(user_id) in users_db

def get_user_data(user_id):
    try:
        return users_db.get(str(user_id))
    except Exception as e:
        logger.error(f"Ошибка чтения пользователя {user_id}: {e}")
        return None

def save_user_data(user_data):
    try:
        users_db[str(user_data["user_id"])] = user_data
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователя {user_data['user_id']}: {e}")
        return False

def create_new_user(user_id, username):
    user_data = DEFAULT_USER_DATA.copy()
    user_data["user_id"] = user_id
    user_data["username"] = username
    user_data["created_at"] = datetime.now().isoformat()
    user_data["cat"]["last_update"] = datetime.now().isoformat()
    user_data["last_care_date"] = datetime.now().date().isoformat()
    
    user_data["cat"]["name"] = random.choice(CAT_NAME_OPTIONS)
    user_data["cat"]["photo_index"] = random.randint(0, len(CAT_IMAGES) - 1)
    
    if save_user_data(user_data):
        bot_stats["total_users"] = len(users_db)
        return user_data
    return None

def get_or_create_user(user_id, username):
    user_data = get_user_data(user_id)
    if user_data:
        return user_data
    return create_new_user(user_id, username)

def get_all_users():
    return list(users_db.values())

# === Функции промокодов ===
def load_promocodes():
    return promocodes_db.copy()

def save_promocodes(promocodes):
    try:
        promocodes_db.clear()
        promocodes_db.update(promocodes)
        return True
    except:
        return False

# === Основные функции бота ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_data = get_or_create_user(user.id, user.username or user.first_name)
    
    if user_data:
        caption = (
            f"🎉 Приветик! Посмотри! Кто это в коробочке?\n\n"
            f"Неужели котик? Это твой новый друг - {user_data['cat']['name']}!\n\n"
            f"Ухаживай за ним, зарабатывай монетки и покупай игрушки!\n\n"
            f"💫 За уход за котиком: +3 монеты\n"
            f"⭐ Выполняй задания для монет\n"
            f"💫 Следи за показателями котика!"
        )
        
        await update.message.reply_text(
            caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 ОТКРЫТЬ КОРОБОЧКУ", callback_data='open_box')]])
        )
    else:
        await update.message.reply_text("❌ Ошибка создания профиля. Попробуйте снова.")

async def open_box(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ Ошибка загрузки профиля.")
        return
    
    caption = (
        f"🎉 А вот и твой лучший друг - {user_data['cat']['name']}!\n\n"
        f"Теперь ты можешь ухаживать за ним в меню ухода!\n\n"
        "🪙 Зарабатывай монетки, ухаживая за котиком!\n"
        "🎁 Покупай игрушки и улучшай своего котика!"
    )
    
    await query.edit_message_text(
        caption,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]])
    )

async def main_menu(query, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("😺 Мой котик", callback_data='my_cat')],
        [InlineKeyboardButton("💖 Уход за котиком", callback_data='care_menu')],
        [InlineKeyboardButton("🪙 Заработать монетки", callback_data='earn_coins')],
        [InlineKeyboardButton("🛒 Магазин", callback_data='shop_menu')],
        [InlineKeyboardButton("⭐ Прокачка", callback_data='upgrade_menu')],
        [InlineKeyboardButton("📊 Рейтинг", callback_data='leaderboard')],
        [InlineKeyboardButton("ℹ️ Инструкция", callback_data='instruction')]
    ]
    
    await query.edit_message_text(
        "🏠 Главное меню:\n\nВыбери раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def instruction(query, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 ИНСТРУКЦИЯ ПО УХОДУ ЗА КОТИКОМ:\n\n"
        "😺 **Мой котик** - посмотреть состояние котика\n"
        "💖 **Уход за котиком** - покормить, почистить, поиграть (+3 монетки!)\n"
        "🪙 **Заработать монетки** - выполнить задания\n"
        "🛒 **Магазин** - купить игрушки, лежанки\n"
        "⭐ **Прокачка** - улучшить показатели котика\n"
        "📊 **Рейтинг** - посмотреть таблицу лидеров\n\n"
        "💰 **ЗАРАБОТОК МОНЕТ:**\n"
        "• Уход за котиком: +3 монеты\n"
        "• Просмотр рекламы: +5 монет\n"
        "• Отзыв: +10 монет\n"
        "• Приглашение друга: +15 монет\n\n"
        "💡 **СОВЕТЫ:**\n"
        "• Следи за показателями котика\n"
        "• Регулярно ухаживай за ним\n"
        "• Выполняй задания для монеток"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]])
    )

async def care_menu(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    cat = user_data['cat']
    reward = 3
    
    keyboard = [
        [InlineKeyboardButton(f"🍖 Покормить (+{reward}🪙)", callback_data='care_feed')],
        [InlineKeyboardButton(f"🛁 Помыть (+{reward}🪙)", callback_data='care_clean')],
        [InlineKeyboardButton(f"🎮 Поиграть (+{reward}🪙)", callback_data='care_play')],
        [InlineKeyboardButton(f"💊 Лечить (+{reward}🪙)", callback_data='care_heal')],
        [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
    ]
    
    status_text = (
        f"💖 УХОД ЗА КОТИКОМ:\n\n"
        f"😺 Имя: {cat['name']}\n"
        f"🍖 Голод: {cat['hunger']}/10\n"
        f"🛁 Чистота: {cat['cleanliness']}/10\n"
        f"🎮 Настроение: {cat['mood']}/10\n"
        f"💊 Здоровье: {cat['health']}/10\n"
        f"⭐ Уровень: {cat['level']}\n\n"
        f"💰 Твои монетки: {user_data['coins']}\n"
        f"🎯 Уходов сегодня: {user_data.get('daily_care_count', 0)}/10\n"
        f"💎 Награда за уход: +{reward} монет"
    )
    
    await query.edit_message_text(
        status_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_care_action(query, context: ContextTypes.DEFAULT_TYPE, action):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    today = datetime.now().date().isoformat()
    last_care_date = user_data.get('last_care_date')
    
    if last_care_date != today:
        user_data['daily_care_count'] = 0
        user_data['last_care_date'] = today
    
    if user_data['daily_care_count'] >= 10:
        await query.answer("❌ Достигнут дневной лимит уходов (10/10). Приходи завтра!")
        return
    
    reward = 3
    cat = user_data['cat']
    
    if action == 'feed':
        cat['hunger'] = min(10, cat['hunger'] + 2)
        message = f"🍖 Ты покормил котика! Голод +2"
    elif action == 'clean':
        cat['cleanliness'] = min(10, cat['cleanliness'] + 2)
        message = f"🛁 Ты помыл котика! Чистота +2"
    elif action == 'play':
        cat['mood'] = min(10, cat['mood'] + 2)
        message = f"🎮 Ты поиграл с котиком! Настроение +2"
    elif action == 'heal':
        cat['health'] = min(10, cat['health'] + 2)
        message = f"💊 Ты полечил котика! Здоровье +2"
    
    user_data['coins'] += reward
    user_data['daily_care_count'] += 1
    cat['care_count'] += 1
    cat['last_update'] = datetime.now().isoformat()
    bot_stats["total_care_actions"] += 1
    
    cat['exp'] += 1
    if cat['exp'] >= cat['level'] * 5:
        cat['level'] += 1
        cat['exp'] = 0
        message += f"\n🎉 Поздравляем! {cat['name']} достиг {cat['level']} уровня!"
    
    message += f"\n💰 Получено {reward} монет за уход!"
    
    if save_user_data(user_data):
        await query.answer(message)
        await care_menu(query, context)
    else:
        await query.answer("❌ Ошибка сохранения данных.")

async def earn_coins(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    daily_count = user_data.get('daily_care_count', 0)
    care_earnings = daily_count * 3
    
    keyboard = [
        [InlineKeyboardButton("📱 Посмотреть рекламу (+5 монет)", callback_data='earn_ad')],
        [InlineKeyboardButton("✍️ Написать отзыв (+10 монет)", callback_data='earn_review')],
        [InlineKeyboardButton("📢 Пригласить друга (+15 монет)", callback_data='earn_invite')],
        [InlineKeyboardButton("💖 Ухаживать за котиком", callback_data='care_menu')],
        [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(
        f"🪙 ЗАРАБОТОК МОНЕТОК:\n\n"
        f"💰 Всего монет: {user_data['coins']}\n"
        f"💖 Уходов сегодня: {daily_count}/10\n"
        f"💎 Заработано за уход: +{care_earnings} монет\n\n"
        f"💡 **Способы заработка:**\n"
        f"• Уход за котиком: +3 монеты\n"
        f"• Просмотр рекламы: +5 монет\n"
        f"• Отзыв: +10 монет\n"
        f"• Приглашение друга: +15 монет",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_earn_action(query, context: ContextTypes.DEFAULT_TYPE, action):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    earnings = {'ad': 5, 'review': 10, 'invite': 15}
    task_key = f"earn_{action}"
    
    today = datetime.now().date().isoformat()
    if task_key in user_data['tasks'] and user_data['tasks'][task_key] == today:
        await query.answer("❌ Вы уже выполняли это задание сегодня!")
        return
    
    user_data['coins'] += earnings[action]
    user_data['tasks'][task_key] = today
    
    messages = {
        'ad': "📱 Спасибо за просмотр рекламы! +5 монет",
        'review': "✍️ Спасибо за отзыв! +10 монет", 
        'invite': "📢 Спасибо за приглашение друга! +15 монет"
    }
    
    if save_user_data(user_data):
        await query.answer(messages[action])
        await earn_coins(query, context)
    else:
        await query.answer("❌ Ошибка сохранения данных.")

async def my_cat(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    cat = user_data['cat']
    daily_count = user_data.get('daily_care_count', 0)
    
    status = "😊 Отлично"
    if any(stat <= 3 for stat in [cat['hunger'], cat['cleanliness'], cat['mood'], cat['health']]):
        status = "😐 Нужен уход"
    if any(stat <= 1 for stat in [cat['hunger'], cat['cleanliness'], cat['mood'], cat['health']]):
        status = "😨 Опасно!"
    
    text = (
        f"😺 ИНФОРМАЦИЯ О КОТИКЕ:\n\n"
        f"📛 Имя: {cat['name']}\n"
        f"⭐ Уровень: {cat['level']}\n"
        f"📊 Опыт: {cat['exp']}/{cat['level'] * 5}\n"
        f"🎯 Статус: {status}\n\n"
        f"📊 ПОКАЗАТЕЛИ:\n"
        f"🍖 Голод: {cat['hunger']}/10\n"
        f"🛁 Чистота: {cat['cleanliness']}/10\n"
        f"🎮 Настроение: {cat['mood']}/10\n"
        f"💊 Здоровье: {cat['health']}/10\n\n"
        f"💰 Монетки: {user_data['coins']}\n"
        f"❤️ Всего уходов: {cat['care_count']}\n"
        f"📅 Уходов сегодня: {daily_count}/10\n"
        f"💎 Награда за уход: +3 монеты"
    )
    
    keyboard = [
        [InlineKeyboardButton("💖 Ухаживать (+3 монеты)", callback_data='care_menu')],
        [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shop_menu(query, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Игрушки", callback_data='toys_shop')],
        [InlineKeyboardButton("🛏️ Лежанки", callback_data='beds_shop')],
        [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(
        "🛒 МАГАЗИН:\n\nВыбери категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def toys_shop(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    keyboard = []
    for toy_id, toy in TOYS.items():
        has_toy = any(item['name'] == toy_id for item in user_data['inventory'])
        status = "✅ Куплено" if has_toy else f"🪙 {toy['price']} монет"
        button_text = f"{toy['emoji']} {toy['display_name']} - {status}"
        if not has_toy:
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'buy_{toy_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='shop_menu')])
    
    await query.edit_message_text(
        f"🎮 МАГАЗИН ИГРУШЕК:\n\n"
        f"💰 Твои монетки: {user_data['coins']}\n\n"
        f"Выбери игрушку для покупки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def beds_shop(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    keyboard = []
    for bed_id, bed in BEDS.items():
        has_bed = any(item['name'] == bed_id for item in user_data['inventory'])
        status = "✅ Куплено" if has_bed else f"🪙 {bed['price']} монет"
        button_text = f"{bed['emoji']} {bed['display_name']} - {status}"
        if not has_bed:
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'buy_{bed_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='shop_menu')])
    
    await query.edit_message_text(
        f"🛏️ МАГАЗИН ЛЕЖАНОК:\n\n"
        f"💰 Твои монетки: {user_data['coins']}\n\n"
        f"Выбери лежанку для покупки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_buy_action(query, context: ContextTypes.DEFAULT_TYPE, item_id):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    if item_id in TOYS:
        item_data = TOYS[item_id]
        category = 'toys_shop'
        price = item_data['price']
        user_balance = user_data['coins']
    elif item_id in BEDS:
        item_data = BEDS[item_id]
        category = 'beds_shop'
        price = item_data['price']
        user_balance = user_data['coins']
    else:
        await query.answer("❌ Такого предмета нет в магазине!")
        return
    
    if user_balance < price:
        await query.answer(f"❌ Недостаточно монет! Нужно {price} монет.")
        return
    
    if item_id in TOYS or item_id in BEDS:
        if any(item['name'] == item_id for item in user_data['inventory']):
            await query.answer("❌ У тебя уже есть этот предмет!")
            return
    
    user_data['coins'] -= price
    user_data['inventory'].append({
        'name': item_id,
        'type': 'toy' if item_id in TOYS else 'bed',
        'purchased_at': datetime.now().isoformat()
    })
    success_message = f"✅ Ты купил {item_data['display_name']}!"
    
    if save_user_data(user_data):
        await query.answer(success_message)
        if category == 'toys_shop':
            await toys_shop(query, context)
        elif category == 'beds_shop':
            await beds_shop(query, context)
    else:
        await query.answer("❌ Ошибка сохранения данных.")

async def upgrade_cat_menu(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    cat = user_data['cat']
    
    keyboard = [
        [InlineKeyboardButton(f"🍖 Улучшить голод (10 монет) - ур. {cat['hunger']}", callback_data='upgrade_hunger')],
        [InlineKeyboardButton(f"🛁 Улучшить чистоту (10 монет) - ур. {cat['cleanliness']}", callback_data='upgrade_cleanliness')],
        [InlineKeyboardButton(f"🎮 Улучшить настроение (10 монет) - ур. {cat['mood']}", callback_data='upgrade_mood')],
        [InlineKeyboardButton(f"💊 Улучшить здоровье (10 монет) - ур. {cat['health']}", callback_data='upgrade_health')],
        [InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(
        "⭐ ПРОКАЧКА КОТИКА:\n\n"
        "Улучшай показатели своего котика!\n"
        f"💰 Твои монетки: {user_data['coins']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_upgrade_action(query, context: ContextTypes.DEFAULT_TYPE, action):
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    cost = 10
    
    if user_data['coins'] < cost:
        await query.answer(f"❌ Недостаточно монет! Нужно {cost} монет.")
        return
    
    cat = user_data['cat']
    stat_names = {
        'hunger': 'голод',
        'cleanliness': 'чистоту', 
        'mood': 'настроение',
        'health': 'здоровье'
    }
    
    if cat[action] >= 10:
        await query.answer(f"❌ {stat_names[action].title()} уже максимального уровня!")
        return
    
    cat[action] += 1
    user_data['coins'] -= cost
    
    if save_user_data(user_data):
        await query.answer(f"✅ Ты улучшил {stat_names[action]} котика до уровня {cat[action]}!")
        await upgrade_cat_menu(query, context)
    else:
        await query.answer("❌ Ошибка сохранения данных.")

async def show_leaderboard(query, context: ContextTypes.DEFAULT_TYPE):
    users = get_all_users()
    
    for user in users:
        if 'cat' in user:
            cat = user['cat']
            rating = cat['level'] * 10 + cat['care_count']
            user['calculated_rating'] = rating
    
    users.sort(key=lambda x: x.get('calculated_rating', 0), reverse=True)
    
    text = "📊 ТОП-10 ИГРОКОВ:\n\n"
    
    for i, user in enumerate(users[:10], 1):
        username = user.get('username', f"Игрок {user.get('user_id', 'Unknown')}")
        cat = user.get('cat', {})
        text += f"{i}. {username} - ⭐ Ур. {cat.get('level', 1)} | ❤️ {cat.get('care_count', 0)} уходов\n"
    
    if not users:
        text += "Пока никого в рейтинге!"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "💌 ОБРАТНАЯ СВЯЗЬ:\n\n"
        "Если у тебя есть предложения или ты нашел ошибку, "
        "напиши нам: @KittyCitySupport\n\n"
        "Мы всегда рады услышать твое мнение! 💖"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    
    uptime = datetime.now() - datetime.fromisoformat(bot_stats["start_time"])
    hours = uptime.total_seconds() / 3600
    
    stats_text = (
        f"📊 СТАТИСТИКА БОТА:\n\n"
        f"👥 Всего пользователей: {bot_stats['total_users']}\n"
        f"❤️ Всего уходов: {bot_stats['total_care_actions']}\n"
        f"⏰ Аптайм: {hours:.1f} часов\n"
        f"🐱 Активных котиков: {len(users_db)}"
    )
    
    await update.message.reply_text(stats_text)

# === Промокоды ===
async def use_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("❌ Использование: /promo <код>")
        return
    
    promo_code = context.args[0].upper()
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ Ошибка загрузки профиля.")
        return
    
    promocodes = load_promocodes()
    
    if promo_code not in promocodes:
        await update.message.reply_text("❌ Промокод не найден или недействителен!")
        return
    
    promo_data = promocodes[promo_code]
    
    if 'expires' in promo_data:
        expires = datetime.fromisoformat(promo_data['expires'])
        if datetime.now() > expires:
            await update.message.reply_text("❌ Срок действия промокода истек!")
            return
    
    if promo_data.get('used', 0) >= promo_data.get('limit', 1):
        await update.message.reply_text("❌ Промокод уже использован максимальное количество раз!")
        return
    
    if promo_code in user_data['used_promocodes']:
        await update.message.reply_text("❌ Ты уже использовал этот промокод!")
        return
    
    reward = promo_data['reward']
    user_data['coins'] += reward
    user_data['used_promocodes'].append(promo_code)
    
    promo_data['used'] = promo_data.get('used', 0) + 1
    promocodes[promo_code] = promo_data
    
    if save_user_data(user_data) and save_promocodes(promocodes):
        await update.message.reply_text(f"🎉 Промокод активирован! Получено {reward} монет!")
    else:
        await update.message.reply_text("❌ Ошибка активации промокода!")

async def new_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Эта команда только для администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /newpromo <код> <награда> [лимит] [дни]")
        return
    
    promo_code = context.args[0].upper()
    try:
        reward = int(context.args[1])
        limit = int(context.args[2]) if len(context.args) > 2 else 1
        days = int(context.args[3]) if len(context.args) > 3 else 30
    except ValueError:
        await update.message.reply_text("❌ Неверный формат чисел!")
        return
    
    promocodes = load_promocodes()
    
    if promo_code in promocodes:
        await update.message.reply_text("❌ Такой промокод уже существует!")
        return
    
    promo_data = {
        'reward': reward,
        'limit': limit,
        'used': 0,
        'created': datetime.now().isoformat(),
        'expires': (datetime.now() + timedelta(days=days)).isoformat()
    }
    
    promocodes[promo_code] = promo_data
    
    if save_promocodes(promocodes):
        await update.message.reply_text(
            f"✅ Промокод создан!\n"
            f"Код: {promo_code}\n"
            f"Награда: {reward} монет\n"
            f"Лимит: {limit} использований\n"
            f"Действует: {days} дней"
        )
    else:
        await update.message.reply_text("❌ Ошибка создания промокода!")

# === Обработчик кнопок ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'open_box':
        await open_box(query, context)
    elif data == 'main_menu':
        await main_menu(query, context)
    elif data == 'instruction':
        await instruction(query, context)
    elif data == 'care_menu':
        await care_menu(query, context)
    elif data == 'care_feed':
        await handle_care_action(query, context, 'feed')
    elif data == 'care_clean':
        await handle_care_action(query, context, 'clean')
    elif data == 'care_play':
        await handle_care_action(query, context, 'play')
    elif data == 'care_heal':
        await handle_care_action(query, context, 'heal')
    elif data == 'earn_coins':
        await earn_coins(query, context)
    elif data == 'earn_ad':
        await handle_earn_action(query, context, 'ad')
    elif data == 'earn_review':
        await handle_earn_action(query, context, 'review')
    elif data == 'earn_invite':
        await handle_earn_action(query, context, 'invite')
    elif data == 'my_cat':
        await my_cat(query, context)
    elif data == 'shop_menu':
        await shop_menu(query, context)
    elif data == 'toys_shop':
        await toys_shop(query, context)
    elif data == 'beds_shop':
        await beds_shop(query, context)
    elif data.startswith('buy_'):
        item_id = data.replace('buy_', '')
        await handle_buy_action(query, context, item_id)
    elif data == 'upgrade_menu':
        await upgrade_cat_menu(query, context)
    elif data == 'upgrade_hunger':
        await handle_upgrade_action(query, context, 'hunger')
    elif data == 'upgrade_cleanliness':
        await handle_upgrade_action(query, context, 'cleanliness')
    elif data == 'upgrade_mood':
        await handle_upgrade_action(query, context, 'mood')
    elif data == 'upgrade_health':
        await handle_upgrade_action(query, context, 'health')
    elif data == 'leaderboard':
        await show_leaderboard(query, context)

# === Автообновление показателей ===
async def auto_update_stats(context: ContextTypes.DEFAULT_TYPE):
    users = get_all_users()
    updated_count = 0
    
    for user_data in users:
        try:
            if not user_data or 'cat' not in user_data:
                continue
            
            cat = user_data['cat']
            if not cat.get('last_update'):
                continue
                
            last_update = datetime.fromisoformat(cat['last_update'])
            
            if datetime.now() - last_update > timedelta(hours=6):  # Увеличили до 6 часов для оптимизации
                cat['hunger'] = max(0, cat['hunger'] - 1)
                cat['cleanliness'] = max(0, cat['cleanliness'] - 1)
                cat['mood'] = max(0, cat['mood'] - 1)
                
                if all(stat == 0 for stat in [cat['hunger'], cat['cleanliness'], cat['mood'], cat['health']]):
                    cat.update({
                        'hunger': 5,
                        'cleanliness': 5,
                        'mood': 5,
                        'health': 5,
                        'level': max(1, cat['level'] - 1),
                        'exp': 0
                    })
                
                cat['last_update'] = datetime.now().isoformat()
                
                if save_user_data(user_data):
                    updated_count += 1
                    
        except Exception as e:
            continue
    
    if updated_count > 0:
        logger.info(f"Автообновление: обновлено {updated_count} пользователей")

# === Основная функция ===
def main() -> None:
    print("🚀 Запуск Kitty City Bot на Replit...")
    print("💾 Используется база данных в памяти")
    print(f"🤖 Токен бота: {'установлен' if BOT_TOKEN else 'НЕ УСТАНОВЛЕН'}")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("feedback", feedback))
    application.add_handler(CommandHandler("promo", use_promo_command))
    application.add_handler(CommandHandler("newpromo", new_promo_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Автоматическое обновление показателей каждые 6 часов
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_update_stats, interval=21600, first=10)
    
    print("✅ Бот успешно запущен!")
    print("🐱 Kitty City Bot готов к работе!")
    print(f"👥 Пользователей в базе: {len(users_db)}")
    
    # Запускаем бота
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
