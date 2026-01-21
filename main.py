from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN
from database import init_db
from handlers.commands import (
    start, help_command, add_task_command, list_tasks_command,
    complete_task_command, delete_task_command
)
from handlers.callbacks import callback_handler
from handlers.messages import handle_message

def main():
    init_db()
    
    if not BOT_TOKEN:
        print("Ошибка! Токен бота не найден.")
        print("Создайте файл .env и добавьте в него строку:")
        print("BOT_TOKEN=ваш_токен_здесь")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add_task", add_task_command))
    application.add_handler(CommandHandler("list_tasks", list_tasks_command))
    application.add_handler(CommandHandler("complete_task", complete_task_command))
    application.add_handler(CommandHandler("delete_task", delete_task_command))
    
    # Обработчик callback-кнопок
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Обработчик обычных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
