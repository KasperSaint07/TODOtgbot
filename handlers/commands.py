from telegram import Update
from telegram.ext import ContextTypes
from core.config import MAIN_MENU_TEXT, HELP_TEXT, ADD_TASK_INSTRUCTIONS, ADD_LATE_INSTRUCTIONS
from ui.keyboards import get_main_menu_keyboard, get_back_menu_keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(MAIN_MENU_TEXT, reply_markup=get_main_menu_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = get_main_menu_keyboard()
    if update.message:
        await update.message.reply_text(HELP_TEXT, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(HELP_TEXT, reply_markup=keyboard)
        await update.callback_query.answer()

async def add_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(ADD_TASK_INSTRUCTIONS)

async def list_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.callbacks import show_list_filter
    if not update.message:
        return
    await show_list_filter(update, context)

async def complete_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from core.database import load_tasks, update_task
    if not update.message or not context.args:
        await update.message.reply_text("Укажите ID задания.\nПример: /complete_task 1")
        return
    
    try:
        task_id = int(context.args[0])
        tasks = load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task:
            update_task(task_id, completed=True)
            await update.message.reply_text(f"Задание #{task_id} отмечено как выполненное!")
        else:
            await update.message.reply_text(f"Задание с ID {task_id} не найдено.")
    except ValueError:
        await update.message.reply_text("ID должен быть числом!")

async def delete_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from core.database import delete_task_by_id
    from ui.keyboards import get_main_menu_keyboard
    if not update.message or not context.args:
        await update.message.reply_text("Укажите ID задания.\nПример: /delete_task 1")
        return
    
    try:
        task_id = int(context.args[0])
        delete_task_by_id(task_id)
        await update.message.reply_text(f"Задание #{task_id} удалено!", reply_markup=get_main_menu_keyboard())
    except ValueError:
        await update.message.reply_text("ID должен быть числом!")

async def add_late_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        keyboard = get_back_menu_keyboard()
        await update.callback_query.edit_message_text(ADD_LATE_INSTRUCTIONS, reply_markup=keyboard)
        await update.callback_query.answer()
        context.user_data['waiting_for_late'] = True
    elif update.message:
        await update.message.reply_text(ADD_LATE_INSTRUCTIONS, reply_markup=get_main_menu_keyboard())
        context.user_data['waiting_for_late'] = True
