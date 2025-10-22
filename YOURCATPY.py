import os
import logging
import json
import random
import asyncio
import requests
import threading
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from flask import Flask
from threading import Thread
import urllib3
from concurrent.futures import ThreadPoolExecutor

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === КОНФИГУРАЦИЯ ===
REPL_OWNER = "timabrilevich"
REPL_SLUG = "KittyCitySuperBot-1"
YANDEX_TOKEN = "y0__xDo1ejABhjblgMgr8ek6xT0N1yRgkT9l_OLaTYIDPPD5wSscA"
BOT_TOKEN = os.getenv("BOT_TOKEN", "8429919809:AAE5lMwVmH86X58JFDxYRPA3bDbFMgSgtsw")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5531546741"))

print(f"🚀 Replit Info: {REPL_OWNER}.{REPL_SLUG}")

# === URL для самопингов ===
SELF_URLS = [
    f"https://{REPL_SLUG}.{REPL_OWNER}.repl.co/",
    f"https://{REPL_SLUG}.{REPL_OWNER}.repl.co/ping", 
    f"https://{REPL_SLUG}.{REPL_OWNER}.repl.co/health",
    f"https://{REPL_SLUG}.{REPL_OWNER}.repl.co/status",
    f"https://{REPL_SLUG}.{REPL_OWNER}.repl.co/api/v1/keepalive"
]

# === HYPER-PING СЕРВИС ===
app = Flask(__name__)

@app.route('/')
def home(): 
    return f"🐱 Kitty Bot 24/7 | {datetime.now().strftime('%H:%M:%S')} | Users: {len(users_db)}"

@app.route('/ping')
def ping(): return "pong"

@app.route('/health')
def health(): return "OK"

@app.route('/status')
def status(): return "🟢 ONLINE"

@app.route('/api/v1/keepalive')
def keepalive(): return {"status": "active", "timestamp": datetime.now().isoformat()}

@app.route('/api/v1/stats')
def stats(): 
    return {
        "users": len(users_db),
        "uptime": str(datetime.now() - start_time),
        "last_ping": last_ping_time.strftime('%H:%M:%S'),
        "ping_count": ping_count
    }

# Глобальные переменные для пингов
start_time = datetime.now()
last_ping_time = datetime.now()
ping_count = 0
users_db = {}
promocodes_db = {}

# === АГРЕССИВНЫЕ ПИНГИ ===
def hyper_ping_worker(url):
    """Рабочий для пинга одного URL"""
    try:
        response = requests.get(url, timeout=10, verify=False)
        return f"✅ {url} - {response.status_code}"
    except Exception as e:
        return f"❌ {url} - {str(e)}"

def hyper_pinging():
    """ГИПЕР-АГРЕССИВНЫЕ ПИНГИ 24/7"""
    global last_ping_time, ping_count
    
    # ОЧЕНЬ частые пинги - каждые 30-90 секунд!
    ping_intervals = [30, 45, 60, 75, 90]  # Случайные интервалы
    
    while True:
        try:
            current_interval = random.choice(ping_intervals)
            
            # Внешние пинги для сетевой активности
            external_urls = [
                "https://www.google.com",
                "https://api.telegram.org",
                "https://yandex.ru",
                "https://github.com",
                "https://stackoverflow.com",
                "https://httpbin.org/get",
                "https://jsonplaceholder.typicode.com/posts/1"
            ]
            
            all_urls = SELF_URLS + external_urls
            
            # Многопоточные пинги для скорости
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(hyper_ping_worker, all_urls))
            
            ping_count += 1
            last_ping_time = datetime.now()
            
            # Логируем каждые 10 пингов
            if ping_count % 10 == 0:
                success_count = sum(1 for r in results if '✅' in r)
                print(f"🎯 Пинг #{ping_count} | Успешно: {success_count}/{len(all_urls)} | Время: {last_ping_time.strftime('%H:%M:%S')}")
            
            # Случайная пауза между 30 и 90 секундами
            time.sleep(current_interval)
            
        except Exception as e:
            print(f"❌ Ошибка пинга: {e}")
            time.sleep(60)  # Пауза при ошибке

def start_hyper_ping():
    """Запуск гипер-пингов в отдельном потоке"""
    ping_thread = Thread(target=hyper_pinging)
    ping_thread.daemon = True
    ping_thread.start()
    print("🚀 HYPER-PING запущен! Интервалы: 30-90 секунд")

# === ЯНДЕКС ДИСК ХРАНИЛИЩЕ ===
class YandexDiskStorage:
    def __init__(self):
        self.token = YANDEX_TOKEN
        self.base_url = "https://cloud-api.yandex.net/v1/disk/resources"
        self.headers = {"Authorization": f"OAuth {self.token}"}
        
        # Создаем папку при инициализации
        self.setup_folder()
    
    def setup_folder(self):
        """Создает папку для бота на Яндекс Диске"""
        try:
            # Создаем основную папку
            response = requests.put(
                f"{self.base_url}?path=/kitty_bot", 
                headers=self.headers
            )
            
            # Создаем подпапку для пользователей
            response2 = requests.put(
                f"{self.base_url}?path=/kitty_bot/users", 
                headers=self.headers
            )
            
            if response.status_code in [201, 409]:
                print("✅ Папка kitty_bot готова на Яндекс Диске!")
                return True
            else:
                print(f"⚠️ Не удалось создать папку: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка создания папки: {e}")
            return False
    
    def save_user_data(self, user_data):
        try:
            user_id = user_data["user_id"]
            filename = f"kitty_bot/users/{user_id}.json"
            
            # Создаем временный файл
            temp_file = f"temp_{user_id}.json"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, ensure_ascii=False, indent=2, default=str)
            
            # Получаем URL для загрузки
            upload_url = f"{self.base_url}/upload?path={filename}&overwrite=true"
            response = requests.get(upload_url, headers=self.headers)
            
            if response.status_code == 200:
                upload_data = response.json()
                
                # Загружаем файл
                with open(temp_file, 'rb') as f:
                    upload_response = requests.put(upload_data['href'], files={'file': f})
                
                os.remove(temp_file)
                
                if upload_response.status_code == 201:
                    print(f"💾 Сохранен пользователь {user_id} в Яндекс Диск")
                    return True
                else:
                    print(f"❌ Ошибка загрузки файла: {upload_response.status_code}")
                    return False
            else:
                print(f"❌ Не удалось получить URL для загрузки: {response.status_code}")
                os.remove(temp_file)
                return False
            
        except Exception as e:
            print(f"❌ Ошибка сохранения Яндекс: {e}")
            if os.path.exists(f"temp_{user_id}.json"):
                os.remove(f"temp_{user_id}.json")
            return False
    
    def load_user_data(self, user_id):
        try:
            filename = f"kitty_bot/users/{user_id}.json"
            download_url = f"{self.base_url}/download?path={filename}"
            response = requests.get(download_url, headers=self.headers)
            
            if response.status_code == 200:
                download_data = response.json()
                file_response = requests.get(download_data['href'])
                
                if file_response.status_code == 200:
                    user_data = json.loads(file_response.text)
                    print(f"📥 Загружен пользователь {user_id} из Яндекс Диска")
                    return user_data
            
            print(f"⚠️ Пользователь {user_id} не найден в Яндекс Диске")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка загрузки Яндекс: {e}")
            return None
    
    def user_exists(self, user_id):
        try:
            filename = f"kitty_bot/users/{user_id}.json"
            url = f"{self.base_url}?path={filename}"
            response = requests.get(url, headers=self.headers)
            return response.status_code == 200
        except:
            return False

# Инициализация хранилища
storage = YandexDiskStorage()

# === ДАННЫЕ ИГРЫ ===
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

# === ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ===
def get_user_data(user_id):
    # Сначала пробуем из памяти
    if str(user_id) in users_db:
        return users_db[str(user_id)]
    
    # Потом из Яндекс Диска
    data = storage.load_user_data(user_id)
    if data:
        users_db[str(user_id)] = data
    return data

def save_user_data(user_data):
    try:
        user_id = user_data["user_id"]
        users_db[str(user_id)] = user_data
        
        # Сохраняем в Яндекс Диск (асинхронно)
        def async_save():
            storage.save_user_data(user_data)
        
        save_thread = Thread(target=async_save)
        save_thread.daemon = True
        save_thread.start()
        
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def user_exists(user_id):
    return str(user_id) in users_db or storage.user_exists(user_id)

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
        return user_data
    return None

def get_or_create_user(user_id, username):
    user_data = get_user_data(user_id)
    if user_data:
        return user_data
    return create_new_user(user_id, username)

def get_all_users():
    return list(users_db.values())

# === ОСНОВНЫЕ ФУНКЦИИ БОТА ===
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

# === ОБРАБОТЧИК КНОПОК ===
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

# === ЗАПУСК ВСЕГО ===
def run_flask():
    """Запуск Flask сервера"""
    app.run(host='0.0.0.0', port=8080, debug=False)

def keep_alive():
    """Запуск всего что нужно для 24/7"""
    # 1. Flask сервер
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # 2. Гипер-пинги (через 10 секунд после запуска)
    time.sleep(10)
    start_hyper_ping()
    
    print("✅ Все системы запущены для 24/7 работы!")

# Запускаем ВСЕ сразу
keep_alive()

# === ОСНОВНАЯ ФУНКЦИЯ ===
def main() -> None:
    print("🚀 ЗАПУСК KITTY BOT 24/7 MODE")
    print(f"⏰ Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Replit: {REPL_OWNER}.{REPL_SLUG}")
    print("🎯 Цель: 20-24 часа автономной работы")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", lambda u,c: u.message.reply_text("🟢 Бот работает 24/7!")))
    
    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Бот запущен в режиме 24/7!")
    print("🔧 HYPER-PING активен каждые 30-90 секунд")
    
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
