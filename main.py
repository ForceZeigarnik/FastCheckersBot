import logging
import sqlite3
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler
)

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
ADMIN_ID = 123456789  # Замените на ваш ID в Telegram
DB_NAME = 'howgaybot.db'
TEXT_INPUT = 1

# Инициализация БД
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица настроек
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Таблица рейтингов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            user_id INTEGER,
            username TEXT,
            rating INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Начальные настройки
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('percentage_text', '🌈 Ваш показатель: {percentage}%')
    ''')
    
    conn.commit()
    conn.close()

# Работа с настройками
def get_setting(key):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def update_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO settings (key, value)
        VALUES (?, ?)
    ''', (key, value))
    conn.commit()
    conn.close()

# Работа с рейтингами
def save_rating(user_id, username, rating):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ratings (user_id, username, rating)
        VALUES (?, ?, ?)
    ''', (user_id, username, rating))
    conn.commit()
    conn.close()

def get_stats(days):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT AVG(rating) 
        FROM ratings 
        WHERE timestamp >= datetime('now', ?)
    ''', (f'-{days} days',))
    result = cursor.fetchone()
    conn.close()
    return round(result[0], 1) if result[0] else 0.0

# Команды пользователя
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    rating = random.randint(0, 100)
    save_rating(user.id, user.username, rating)
    
    text_template = get_setting('percentage_text')
    response = text_template.format(percentage=rating)
    
    update.message.reply_text(response)

def stats(update: Update, context: CallbackContext):
    stats_7 = get_stats(7)
    stats_30 = get_stats(30)
    stats_365 = get_stats(365)
    
    response = (
        "📊 Статистика сообщества:\n\n"
        f"• За 7 дней: {stats_7}%\n"
        f"• За 30 дней: {stats_30}%\n"
        f"• За 365 дней: {stats_365}%"
    )
    
    update.message.reply_text(response)

# Админ-панель
def admin(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("🚫 Доступ запрещен!")
        return
    
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить текст", callback_data='change_text')],
        [InlineKeyboardButton("📈 Статистика", callback_data='admin_stats')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    current_text = get_setting('percentage_text')
    
    update.message.reply_text(
        f"👑 Админ-панель\n\nТекущий текст: {current_text}",
        reply_markup=reply_markup
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data == 'change_text':
        query.message.reply_text("Введите новый текст (используйте {percentage} для вставки числа):")
        return TEXT_INPUT
    
    elif query.data == 'admin_stats':
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM ratings')
        total = cursor.fetchone()[0]
        conn.close()
        
        query.message.reply_text(
            f"📦 Общая статистика:\n\n"
            f"• Всего измерений: {total}\n"
            f"• Среднее за всё время: {get_stats(365*5)}%"
        )

def update_text(update: Update, context: CallbackContext):
    new_text = update.message.text
    if '{percentage}' not in new_text:
        update.message.reply_text("❌ Ошибка: текст должен содержать {percentage}!")
        return ConversationHandler.END
    
    update_setting('percentage_text', new_text)
    update.message.reply_text("✅ Текст успешно обновлен!")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("🚫 Действие отменено")
    return ConversationHandler.END

def main():
    init_db()
    updater = Updater("YOUR_BOT_TOKEN", use_context=True)
    dp = updater.dispatcher

    # Обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("admin", admin))

    # Обработчик админ-панели
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            TEXT_INPUT: [MessageHandler(Filters.text & ~Filters.command, update_text)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
