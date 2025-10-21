import os
import logging
import json
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Настройка путей для облака
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = SCRIPT_DIR
USERS_PATH = os.path.join(SAVE_PATH, "users")
PROMOCODES_PATH = os.path.join(SAVE_PATH, "promocodes.json")

# Создаем папки если не существуют
os.makedirs(USERS_PATH, exist_ok=True)

# Токены из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "8429919809:AAE5lMwVmH86X58JFDxYRPA3bDbFMgSgtsw")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5531546741"))
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")

# Названия котов (имена файлов)
CAT_IMAGES = [
    "cat1.jpg", "cat2.jpg", "cat3.jpg", "cat4.jpg", "cat5.jpg", 
    "cat7.jpg", "cat8.jpg", "cat9.jpg"
]

# Стандартные настройки нового пользователя
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

# Имена для котов
CAT_NAME_OPTIONS = [
    "Барсик", "Мурзик", "Васька", "Рыжик", "Снежок", "Пушок", "Кузя", "Тигра", 
    "Луна", "Симба", "Оскар", "Гарфилд", "Том", "Феликс", "Чарли", "Макс"
]

# Игрушки
TOYS = {
    'i1': {'name': 'i1', 'price': 20, 'emoji': '🎾', 'display_name': 'Мячик i1'},
    'i2': {'name': 'i2', 'price': 30, 'emoji': '🐟', 'display_name': 'Рыбка i2'},
    'i3': {'name': 'i3', 'price': 40, 'emoji': '🎯', 'display_name': 'Мишень i3'},
    'i4': {'name': 'i4', 'price': 50, 'emoji': '🧶', 'display_name': 'Клубок i4'},
    'i5': {'name': 'i5', 'price': 60, 'emoji': '🐭', 'display_name': 'Мышка i5'},
    'i6': {'name': 'i6', 'price': 70, 'emoji': '🎁', 'display_name': 'Сюрприз i6'},
    'i7': {'name': 'i7', 'price': 80, 'emoji': '🌟', 'display_name': 'Звезда i7'},
    'i8': {'name': 'i8', 'price': 100, 'emoji': '👑', 'display_name': 'Корона i8'}
}

# Лежанки
BEDS = {
    'lezanka1': {'name': 'lezanka1', 'price': 150, 'emoji': '🛏️', 'display_name': 'Лежанка 1'},
    'lezanka2': {'name': 'lezanka2', 'price': 200, 'emoji': '🏠', 'display_name': 'Лежанка 2'},
    'lezanka3': {'name': 'lezanka3', 'price': 250, 'emoji': '🛋️', 'display_name': 'Лежанка 3'},
    'lezanka4': {'name': 'lezanka4', 'price': 300, 'emoji': '🏰', 'display_name': 'Лежанка 4'},
    'lezanka5': {'name': 'lezanka5', 'price': 400, 'emoji': '💎', 'display_name': 'Лежанка 5'}
}

# Пакеты монет для покупки
COIN_PACKAGES = {
    'coins_100': {'coins': 100, 'price': 49, 'currency': 'RUB', 'emoji': '⭐', 'display_name': '100 монет'},
    'coins_250': {'coins': 250, 'price': 99, 'currency': 'RUB', 'emoji': '🌟🌟', 'display_name': '250 монет'},
    'coins_500': {'coins': 500, 'price': 179, 'currency': 'RUB', 'emoji': '🌟🌟🌟', 'display_name': '500 монет'},
    'coins_1000': {'coins': 1000, 'price': 299, 'currency': 'RUB', 'emoji': '💫', 'display_name': '1000 монет'},
}

# Функции для работы с JSON
def get_user_file_path(user_id):
    return os.path.join(USERS_PATH, f"{user_id}.json")

def user_exists(user_id):
    return os.path.exists(get_user_file_path(user_id))

def get_user_data(user_id):
    file_path = get_user_file_path(user_id)
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка чтения файла пользователя {user_id}: {e}")
        return None

def save_user_data(user_data):
    try:
        file_path = get_user_file_path(user_data["user_id"])
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения файла пользователя {user_data['user_id']}: {e}")
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
        return user_data
    return None

def get_or_create_user(user_id, username):
    user_data = get_user_data(user_id)
    if user_data:
        return user_data
    return create_new_user(user_id, username)

def get_cat_photo_path(user_data):
    if not user_data or "cat" not in user_data:
        return None
    photo_index = user_data["cat"].get("photo_index", 0)
    if 0 <= photo_index < len(CAT_IMAGES):
        photo_filename = CAT_IMAGES[photo_index]
        return os.path.join(SCRIPT_DIR, photo_filename)
    return None

async def send_cat_photo(chat_id, context, user_data, caption=""):
    photo_path = get_cat_photo_path(user_data)
    
    if photo_path and os.path.exists(photo_path):
        try:
            with open(photo_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption
                )
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            return False
    else:
        logger.error(f"Фото не найдено по пути: {photo_path}")
        return False

# Функции для работы с платежами
async def buy_coins_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """Меню покупки монет"""
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await query.answer("❌ Ошибка загрузки профиля.")
        return
    
    keyboard = []
    for package_id, package in COIN_PACKAGES.items():
        price_text = f"{package['price']} {package['currency']}"
        button_text = f"{package['emoji']} {package['display_name']} - {price_text}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f'buy_{package_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='earn_coins')])
    
    await query.edit_message_text(
        f"💎 ПОКУПКА МОНЕТ:\n\n"
        f"💰 Твои монетки: {user_data['coins']}\n\n"
        f"🎁 Выбери пакет монет:\n\n"
        f"💳 Оплата банковской картой\n"
        f"🔒 Безопасно через Telegram\n"
        f"⚡ Монетки приходят мгновенно!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, package_id: str):
    """Начинает процесс оплаты"""
    if not PAYMENT_PROVIDER_TOKEN:
        await update.message.reply_text(
            "❌ Платежи временно недоступны.\n"
            "Приносим извинения за неудобства!"
        )
        return
    
    if package_id not in COIN_PACKAGES:
        await update.message.reply_text("❌ Такого пакета не существует!")
        return
    
    package = COIN_PACKAGES[package_id]
    user_id = update.effective_user.id
    
    # Сохраняем информацию о покупке
    context.user_data['pending_payment'] = {
        'package_id': package_id,
        'coins': package['coins'],
        'price': package['price'],
        'currency': package['currency'],
        'user_id': user_id
    }
    
    # Создаем инвойс для оплаты
    title = f"Покупка {package['coins']} монет"
    description = f"Пакет {package['display_name']} для Kitty City"
    payload = f"coin_purchase_{user_id}_{package_id}"
    currency = package['currency']
    prices = [LabeledPrice(f"{package['coins']} монет", package['price'] * 100)]
    
    try:
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title=title,
            description=description,
            payload=payload,
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency=currency,
            prices=prices,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False,
            start_parameter=package_id
        )
    except Exception as e:
        logger.error(f"Ошибка создания инвойса: {e}")
        await update.message.reply_text("❌ Ошибка создания платежа. Попробуйте позже.")

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик предварительной проверки платежа"""
    query = update.pre_checkout_query
    try:
        await query.answer(ok=True)
        logger.info(f"Pre-checkout approved for user {query.from_user.id}")
    except Exception as e:
        logger.error(f"Pre-checkout error: {e}")
        await query.answer(ok=False, error_message="Ошибка обработки платежа")

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик успешного платежа"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    
    pending_payment = context.user_data.get('pending_payment', {})
    
    if not pending_payment or pending_payment['user_id'] != user_id:
        logger.error(f"No pending payment found for user {user_id}")
        await update.message.reply_text("❌ Ошибка обработки платежа. Свяжитесь с поддержкой.")
        return
    
    package_id = pending_payment['package_id']
    coins_to_add = pending_payment['coins']
    
    user_data = get_user_data(user_id)
    if not user_data:
        await update.message.reply_text("❌ Ошибка загрузки профиля.")
        return
    
    # Начисляем монеты
    user_data['coins'] += coins_to_add
    
    if save_user_data(user_data):
        context.user_data.pop('pending_payment', None)
        
        await update.message.reply_text(
            f"🎉 Оплата прошла успешно!\n"
            f"💎 Получено: {coins_to_add} монет\n"
            f"💰 Теперь у тебя: {user_data['coins']} монет\n\n"
            f"Спасибо за покупку! 💖"
        )
        logger.info(f"Successful payment: user {user_id} received {coins_to_add} coins")
    else:
        await update.message.reply_text("❌ Ошибка начисления монет. Свяжитесь с поддержкой.")

# Основные функции бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_data = get_or_create_user(user.id, user.username or user.first_name)
    
    if user_data:
        caption = (
            f"🎉 Приветик! Посмотри! Кто это в коробочке?\n\n"
            f"Неужели котик? Это твой новый друг - {user_data['cat']['name']}!\n\n"
            f"Ухаживай за ним, зарабатывай монетки и покупай игрушки!\n\n"
            f"💫 За уход за котиком: +3 монеты\n"
            f"⭐ Покупай монеты за реальные деньги\n"
            f"💫 Не забывай следить за показателями котика!"
        )
        
        photo_sent = await send_cat_photo(update.effective_chat.id, context, user_data, caption)
        
        if not photo_sent:
            await update.message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 ОТКРЫТЬ КОРОБОЧКУ", callback_data='open_box')]])
            )
        else:
            await update.message.reply_text(
                "📦 Нажми кнопку ниже чтобы открыть коробочку!",
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
        f"🎉 А вот и твой лучший друг!\n\n"
        f"Теперь ты можешь ухаживать за {user_data['cat']['name']} в меню ухода!\n\n"
        "🪙 Зарабатывай монетки, ухаживая за котиком!\n"
        "⭐ Покупай монеты за реальные деньги!\n"
        "🎁 Покупай игрушки и улучшай своего котика!"
    )
    
    photo_sent = await send_cat_photo(query.message.chat_id, context, user_data, caption)
    
    if not photo_sent:
        await query.edit_message_text(
            caption,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]])
        )
    else:
        await query.delete_message()
        await query.message.reply_text(
            "Выбери действие:",
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
        "• Приглашение друга: +15 монет\n"
        "• Покупка за реальные деньги\n\n"
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
        [InlineKeyboardButton("📸 Фото котика", callback_data='care_photo')],
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
    
    if action == 'photo':
        caption = "Твой прекрасный котик! 😺"
        photo_sent = await send_cat_photo(query.message.chat_id, context, user_data, caption)
        
        if not photo_sent:
            await query.message.reply_text("Твой прекрасный котик! 😺\n(Не удалось загрузить фото)")
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
        [InlineKeyboardButton("💎 Купить монеты", callback_data='buy_coins_menu')],
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
        f"• Приглашение друга: +15 монет\n"
        f"• Покупка за реальные деньги",
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
        [InlineKeyboardButton("📸 Фото котика", callback_data='care_photo')],
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
        [InlineKeyboardButton("💎 Купить монеты", callback_data='buy_coins_menu')],
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
    elif item_id in COIN_PACKAGES:
        await start_payment(query, context, item_id)
        return
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
    user_files = [f for f in os.listdir(USERS_PATH) if f.endswith('.json')]
    users = []
    
    for user_file in user_files:
        try:
            user_id = int(user_file.split('.')[0])
            user_data = get_user_data(user_id)
            if user_data:
                cat = user_data['cat']
                rating = cat['level'] * 10 + cat['care_count']
                user_data['calculated_rating'] = rating
                users.append(user_data)
        except:
            continue
    
    users.sort(key=lambda x: x['calculated_rating'], reverse=True)
    
    text = "📊 ТОП-10 ИГРОКОВ:\n\n"
    
    for i, user in enumerate(users[:10], 1):
        username = user['username'] or f"Игрок {user['user_id']}"
        cat = user['cat']
        text += f"{i}. {username} - ⭐ Ур. {cat['level']} | ❤️ {cat['care_count']} уходов\n"
    
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

# Промокоды
def load_promocodes():
    if os.path.exists(PROMOCODES_PATH):
        try:
            with open(PROMOCODES_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_promocodes(promocodes):
    try:
        with open(PROMOCODES_PATH, 'w', encoding='utf-8') as f:
            json.dump(promocodes, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

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

# Автоматическое обновление показателей
async def auto_update_stats(context: ContextTypes.DEFAULT_TYPE):
    user_files = [f for f in os.listdir(USERS_PATH) if f.endswith('.json')]
    updated_count = 0
    
    for user_file in user_files:
        try:
            user_id = int(user_file.split('.')[0])
            user_data = get_user_data(user_id)
            
            if not user_data or 'cat' not in user_data:
                continue
            
            cat = user_data['cat']
            if not cat.get('last_update'):
                continue
                
            last_update = datetime.fromisoformat(cat['last_update'])
            
            if datetime.now() - last_update > timedelta(hours=3):
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
                    
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="😿 Твой котик убежал из-за плохого ухода!\n"
                                 "Но он вернулся немного ослабленным...\n"
                                 "Пожалуйста, лучше ухаживай за ним!"
                        )
                    except:
                        pass
                
                cat['last_update'] = datetime.now().isoformat()
                
                if save_user_data(user_data):
                    updated_count += 1
                    
        except Exception as e:
            logger.error(f"Ошибка обновления пользователя {user_file}: {e}")
            continue
    
    if updated_count > 0:
        logger.info(f"Автообновление: обновлено {updated_count} пользователей")

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Основное меню
    if data == 'open_box':
        await open_box(query, context)
    elif data == 'main_menu':
        await main_menu(query, context)
    elif data == 'instruction':
        await instruction(query, context)
    
    # Уход за котиком
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
    elif data == 'care_photo':
        await handle_care_action(query, context, 'photo')
    
    # Заработок монет
    elif data == 'earn_coins':
        await earn_coins(query, context)
    elif data == 'earn_ad':
        await handle_earn_action(query, context, 'ad')
    elif data == 'earn_review':
        await handle_earn_action(query, context, 'review')
    elif data == 'earn_invite':
        await handle_earn_action(query, context, 'invite')
    elif data == 'buy_coins_menu':
        await buy_coins_menu(query, context)
    
    # Магазин
    elif data == 'shop_menu':
        await shop_menu(query, context)
    elif data == 'toys_shop':
        await toys_shop(query, context)
    elif data == 'beds_shop':
        await beds_shop(query, context)
    elif data.startswith('buy_'):
        item_id = data.replace('buy_', '')
        await handle_buy_action(query, context, item_id)
    
    # Информация о котике
    elif data == 'my_cat':
        await my_cat(query, context)
    
    # Прокачка
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
    
    # Рейтинг
    elif data == 'leaderboard':
        await show_leaderboard(query, context)

def main() -> None:
    # Создаем необходимые папки
    os.makedirs(USERS_PATH, exist_ok=True)
    
    print("🚀 Запуск Kitty City Bot на Railway...")
    print(f"📁 Рабочая директория: {SCRIPT_DIR}")
    print(f"💾 Папка пользователей: {USERS_PATH}")
    
    # Проверяем переменные окружения
    if not BOT_TOKEN or BOT_TOKEN == "8429919809:AAE5lMwVmH86X58JFDxYRPA3bDbFMgSgtsw":
        print("⚠️  Внимание: Используется дефолтный токен бота")
    
    if not PAYMENT_PROVIDER_TOKEN:
        print("⚠️  PAYMENT_PROVIDER_TOKEN не установлен, платежи недоступны")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("feedback", feedback))
    application.add_handler(CommandHandler("promo", use_promo_command))
    application.add_handler(CommandHandler("newpromo", new_promo_command))
    
    # Обработчики платежей
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Автоматическое обновление показателей каждые 3 часа
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_update_stats, interval=10800, first=10)
    
    print("✅ Бот успешно запущен!")
    print("🐱 Kitty City Bot готов к работе!")
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()