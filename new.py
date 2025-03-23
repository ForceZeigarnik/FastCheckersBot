import json
import logging
import random
from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для админ-панели
TEXT_SELECTION, NEW_TEXT = range(2)

# Загрузка конфигурации
with open('config.json', 'r') as f:
    config = json.load(f)

def save_config():
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

# Шутки и генерация результата
JOKES = config.get('jokes', [
    "А ты уверен, что это погрешность измерений?",
    "Радуга сегодня особенно яркая!",
    "Не переживай, это временно... или нет?"
])

def generate_result(percent: int) -> str:
    joke = random.choice(JOKES)
    return config['texts']['result'].format(percent=percent, joke=joke)

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎲 Бот для определения гей-процента!\n"
        "Используйте @username_бота в любом чате!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "✨ Новый результат",
                switch_inline_query_current_chat=""
            )
        ]])
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Просто начните ввод с @username_бота в любом чате!"
    )

# Инлайн-режим
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    percent = random.randint(0, 100)
    result_text = generate_result(percent)
    
    results = [
        InlineQueryResultArticle(
            id=str(random.getrandbits(64)),
            title=f"🎰 Результат: {percent}%",
            description="Нажмите чтобы отправить в чат",
            input_message_content=InputTextMessageContent(result_text)
        )
    ]
    
    await update.inline_query.answer(results, cache_time=0)

# Админ-панель
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config['admin_ids']:
        await update.message.reply_text("🚫 Доступ запрещен!")
        return ConversationHandler.END
    
    keyboard = [[
        InlineKeyboardButton("✏️ Изменить текст", callback_data='edit_text')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔧 Админ-панель:", reply_markup=reply_markup)
    return TEXT_SELECTION

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'edit_text':
        await query.edit_message_text("📝 Введите новый текст (используйте {percent} и {joke}):")
        return NEW_TEXT

async def save_new_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_text = update.message.text
    config['texts']['result'] = new_text
    save_config()
    await update.message.reply_text("✅ Текст успешно обновлен!")
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token("tyttoken").build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(InlineQueryHandler(inline_query))

    # Обработчик админ-панели
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={
            TEXT_SELECTION: [CallbackQueryHandler(button_callback)],
            NEW_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_text)]
        },
        fallbacks=[]
    )
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == "__main__":
    main()
