from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
from config import MAIN_MENU_TEXT, HELP_TEXT, ADD_TASK_INSTRUCTIONS
from database import load_tasks, update_task, delete_task_by_id, load_late_employees
from utils import format_tasks_list, is_overdue
from keyboards import get_main_menu_keyboard, get_list_filter_keyboard, get_back_menu_keyboard
from handlers.commands import add_late_employee

async def show_list_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = get_list_filter_keyboard()
    text = "Выберите категорию заданий:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, reply_markup=keyboard)

async def show_late_employees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    late_list = load_late_employees()
    
    if not late_list:
        message = "Список опозданий пуст! ✅"
    else:
        message = "🚶 Список опоздавших:\n\n"
        
        # Группируем по датам
        by_date = {}
        for late in late_list:
            date = late['date']
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(late)
        
        # Сортируем даты (новые сначала)
        sorted_dates = sorted(by_date.keys(), key=lambda x: datetime.strptime(x, "%d.%m.%Y"), reverse=True)
        
        for date in sorted_dates:
            message += f"📅 {date}:\n"
            for late in by_date[date]:
                employee_display = late['employee_name'] if late['employee_name'] else late['employee']
                time_info = f" - опоздал на {late['late_time']}" if late['late_time'] else ""
                message += f"  • {employee_display} ({late['employee']}){time_info}\n"
                if late['created_by']:
                    message += f"    Отметил: {late['created_by']}\n"
            message += "\n"
    
    keyboard = get_back_menu_keyboard()
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=keyboard)
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(message, reply_markup=keyboard)

async def handle_list_callback(query, filter_func, empty_message):
    tasks = filter_func(load_tasks())
    message, keyboard = format_tasks_list(tasks)
    if message:
        await query.edit_message_text(message, reply_markup=keyboard)
    else:
        await query.edit_message_text(empty_message, reply_markup=get_list_filter_keyboard())

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    data = query.data
    
    if data == "main_menu":
        await query.edit_message_text(MAIN_MENU_TEXT, reply_markup=get_main_menu_keyboard())
    
    elif data == "help":
        await query.edit_message_text(HELP_TEXT, reply_markup=get_main_menu_keyboard())
    
    elif data == "add_task":
        keyboard = get_back_menu_keyboard()
        await query.edit_message_text(ADD_TASK_INSTRUCTIONS, reply_markup=keyboard)
    
    elif data == "list_all":
        await handle_list_callback(query, lambda t: t, "Список заданий пуст.")
    
    elif data == "list_active":
        await handle_list_callback(query, lambda t: [x for x in t if not x["completed"]], "Активных заданий нет.")
    
    elif data == "list_done":
        await handle_list_callback(query, lambda t: [x for x in t if x["completed"]], "Выполненных заданий нет.")
    
    elif data == "list_overdue":
        await handle_list_callback(query, lambda t: [x for x in t if is_overdue(x)], "Просроченных заданий нет.")
    
    elif data == "add_late":
        await add_late_employee(update, context)
    
    elif data == "list_late":
        await show_late_employees(update, context)
    
    elif data.startswith("complete_"):
        task_id = int(data.split("_")[1])
        tasks = load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task:
            update_task(task_id, completed=True)
            await query.answer(f"Задание #{task_id} отмечено как выполненное!")
            tasks = load_tasks()
            message, keyboard = format_tasks_list(tasks)
            if message:
                await query.edit_message_text(message, reply_markup=keyboard)
        else:
            await query.answer("Задание не найдено!")
    
    elif data.startswith("delete_"):
        task_id = int(data.split("_")[1])
        delete_task_by_id(task_id)
        await query.answer(f"Задание #{task_id} удалено!")
        tasks = load_tasks()
        message, keyboard = format_tasks_list(tasks)
        if message:
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            await query.edit_message_text("Список заданий пуст.", reply_markup=get_list_filter_keyboard())
