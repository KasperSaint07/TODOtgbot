import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv()

DB_FILE = "tasks.db"
DATE_FORMATS = ["%d.%m.%Y", "%d.%m.%y"]

MAIN_MENU_TEXT = "Привет! Я бот для управления заданиями.\n\nВыберите действие:"
HELP_TEXT = (
    "Привет! Я бот для управления заданиями.\n\n"
    "Доступные команды:\n"
    "/start или /menu - Главное меню\n"
    "/add_task - Добавить новое задание\n"
    "/list_tasks - Показать все задания\n\n"
    "Выберите действие:"
)
ADD_TASK_INSTRUCTIONS = (
    "Чтобы добавить задание, отправьте сообщение в формате:\n\n"
    "Задание: [описание задания]\n"
    "Дедлайн: [дата: ДД.ММ.ГГГГ или ДД.ММ.ГГ]\n"
    "Сотрудник: @username или имя\n\n"
    "Пример:\n"
    "Задание: Подготовить отчет\n"
    "Дедлайн: 25.12.2024\n"
    "Сотрудник: @ivan_petrov\n\n"
    "Можно использовать короткий формат даты: 10.01.26\n"
    "Можно упомянуть сотрудника через @username прямо в сообщении!"
)

def init_db():
    # Создает таблицу tasks, если она не существует
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            deadline TEXT NOT NULL,
            employee TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _execute_db(query, params=None, fetch=False):
    # Вспомогательная функция для выполнения запросов к БД
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    result = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return result



def load_tasks():
    # Загружает все задания из базы данных
    rows = _execute_db("SELECT id, task, deadline, employee, completed, created_at FROM tasks", fetch=True)
    return [{
        "id": row[0],
        "task": row[1],
        "deadline": row[2],
        "employee": row[3],
        "completed": bool(row[4]),
        "created_at": row[5]
    } for row in rows]

def insert_task(task, deadline, employee, created_at):
    # Добавляет новое задание в базу данных
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (task, deadline, employee, completed, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (task, deadline, employee, 0, created_at))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def update_task(task_id, completed=None, task=None, deadline=None, employee=None):
    # Обновляет задание в базе данных
    updates = []
    params = []
    
    if completed is not None:
        updates.append("completed = ?")
        params.append(1 if completed else 0)
    if task is not None:
        updates.append("task = ?")
        params.append(task)
    if deadline is not None:
        updates.append("deadline = ?")
        params.append(deadline)
    if employee is not None:
        updates.append("employee = ?")
        params.append(employee)
    
    if updates:
        params.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        _execute_db(query, params)

def delete_task_by_id(task_id):
    # Удаляет задание из базы данных по ID
    _execute_db("DELETE FROM tasks WHERE id = ?", (task_id,))

def normalize_username(username):
    # Нормализует username - добавляет @ если нужно
    if not username or username == "Не указан" or username.startswith("@"):
        return username
    if username.replace("_", "").replace("-", "").isalnum():
        return f"@{username}"
    return username

def parse_date(date_str):
    # Парсит дату в формате ДД.ММ.ГГГГ или ДД.ММ.ГГ
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue
    return None

def deadline_to_datetime(deadline_str):
    # Конвертирует строку дедлайна в datetime для сортировки
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(deadline_str, fmt)
        except ValueError:
            continue
    return datetime.max

def is_overdue(task):
    # Проверяет, просрочено ли задание
    if task["completed"]:
        return False
    deadline_date = deadline_to_datetime(task["deadline"])
    return deadline_date.date() < datetime.now().date()

def get_task_status(task):
    # Возвращает статус задания с эмодзи
    if task["completed"]:
        return "✅ Completed"
    elif is_overdue(task):
        return "⏰ Overdue"
    else:
        return "🟢 In progress"

def get_main_menu_keyboard():
    # Создает клавиатуру главного меню
    keyboard = [
        [InlineKeyboardButton("➕ Добавить задание", callback_data="add_task")],
        [InlineKeyboardButton("📋 Все задания", callback_data="list_all")],
        [InlineKeyboardButton("🟢 Активные", callback_data="list_active")],
        [InlineKeyboardButton("✅ Выполненные", callback_data="list_done")],
        [InlineKeyboardButton("⏰ Просроченные", callback_data="list_overdue")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_list_filter_keyboard():
    # Создает клавиатуру для фильтрации заданий
    keyboard = [
        [InlineKeyboardButton("📋 Все задания", callback_data="list_all")],
        [InlineKeyboardButton("🟢 Активные", callback_data="list_active")],
        [InlineKeyboardButton("✅ Выполненные", callback_data="list_done")],
        [InlineKeyboardButton("⏰ Просроченные", callback_data="list_overdue")],
        [InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

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

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(ADD_TASK_INSTRUCTIONS)

def _parse_task_message(text, entities):
    # Парсит сообщение с заданием и возвращает task_desc, deadline, employee
    task_desc = ""
    deadline = ""
    employee = ""
    
    for line in text.split('\n'):
        line = line.strip()
        line_lower = line.lower()
        if line_lower.startswith("задание:"):
            task_desc = line[line.find(":") + 1:].strip()
        elif line_lower.startswith("дедлайн:"):
            deadline = line[line.find(":") + 1:].strip()
        elif line_lower.startswith("сотрудник:"):
            employee = line[line.find(":") + 1:].strip()
    
    if not employee and entities:
        for entity in entities:
            if entity.type == "mention":
                employee = text[entity.offset:entity.offset + entity.length]
                break
            elif entity.type == "text_mention" and entity.user:
                employee = f"@{entity.user.username}" if entity.user.username else entity.user.first_name
                break
    
    return task_desc, deadline, employee

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    if text.startswith("/add_task"):
        text = text.replace("/add_task", "").strip()
    
    text_lower = text.lower()
    if "задание:" not in text_lower or "дедлайн:" not in text_lower:
        await update.message.reply_text(
            "Не понимаю это сообщение. Используйте команды:\n"
            "/add_task - чтобы узнать, как добавить задание\n"
            "/list_tasks - чтобы посмотреть все задания"
        )
        return
    
    task_desc, deadline, employee = _parse_task_message(text, update.message.entities)
    employee = normalize_username(employee) if employee else "Не указан"
    
    if not task_desc or not deadline:
        await update.message.reply_text("Ошибка! Укажите задание и дедлайн.")
        return
    
    deadline_formatted = parse_date(deadline)
    if not deadline_formatted:
        await update.message.reply_text(
            "Неверный формат даты! Используйте:\n"
            "• ДД.ММ.ГГГГ (например, 10.01.2026)\n"
            "• ДД.ММ.ГГ (например, 10.01.26)"
        )
        return
    
    created_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    task_id = insert_task(task_desc, deadline_formatted, employee, created_at)
    
    await update.message.reply_text(
        f"Задание добавлено!\n\n"
        f"Задание: {task_desc}\n"
        f"Дедлайн: {deadline_formatted}\n"
        f"Сотрудник: {employee}",
        reply_markup=get_main_menu_keyboard()
    )

async def show_list_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Показывает кнопки фильтрации заданий
    keyboard = get_list_filter_keyboard()
    text = "Выберите категорию заданий:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, reply_markup=keyboard)

def format_tasks_list(tasks, show_buttons=True):
    # Форматирует список заданий с кнопками управления
    if not tasks:
        return None, None
    
    tasks.sort(key=lambda t: deadline_to_datetime(t["deadline"]))
    
    message = "Список заданий:\n\n"
    keyboard_buttons = []
    
    for task in tasks:
        status = get_task_status(task)
        employee = normalize_username(task['employee'])
        
        message += f"ID: {task['id']}\n"
        message += f"{task['task']}\n"
        message += f"Дедлайн: {task['deadline']}\n"
        message += f"Сотрудник: {employee}\n"
        message += f"Статус: {status}\n"
        message += f"Создано: {task['created_at']}\n\n"
        
        if show_buttons:
            task_buttons = []
            if not task["completed"]:
                task_buttons.append(InlineKeyboardButton(
                    "✅ Выполнить", 
                    callback_data=f"complete_{task['id']}"
                ))
            task_buttons.append(InlineKeyboardButton(
                "🗑️ Удалить", 
                callback_data=f"delete_{task['id']}"
            ))
            keyboard_buttons.append(task_buttons)
    
    if show_buttons:
        keyboard_buttons.append([InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
    else:
        keyboard = None
    
    return message, keyboard

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Команда /list_tasks - показывает кнопки фильтра
    if not update.message:
        return
    await show_list_filter(update, context)

async def complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not context.args:
        await update.message.reply_text("Укажите ID задания.\nПример: /delete_task 1")
        return
    
    try:
        task_id = int(context.args[0])
        delete_task_by_id(task_id)
        await update.message.reply_text(f"Задание #{task_id} удалено!", reply_markup=get_main_menu_keyboard())
    except ValueError:
        await update.message.reply_text("ID должен быть числом!")

def _handle_list_callback(query, filter_func, empty_message):
    # Обработка callback для фильтрации списка заданий
    tasks = filter_func(load_tasks())
    message, keyboard = format_tasks_list(tasks)
    if message:
        return query.edit_message_text(message, reply_markup=keyboard)
    else:
        return query.edit_message_text(empty_message, reply_markup=get_list_filter_keyboard())

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обработчик всех callback-запросов от кнопок
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
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")
        ]])
        await query.edit_message_text(ADD_TASK_INSTRUCTIONS, reply_markup=keyboard)
    
    elif data == "list_all":
        await _handle_list_callback(query, lambda t: t, "Список заданий пуст.")
    
    elif data == "list_active":
        await _handle_list_callback(query, lambda t: [x for x in t if not x["completed"]], "Активных заданий нет.")
    
    elif data == "list_done":
        await _handle_list_callback(query, lambda t: [x for x in t if x["completed"]], "Выполненных заданий нет.")
    
    elif data == "list_overdue":
        await _handle_list_callback(query, lambda t: [x for x in t if is_overdue(x)], "Просроченных заданий нет.")
    
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

def main():
    init_db()
    
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        print("Ошибка! Токен бота не найден.")
        print("Создайте файл .env и добавьте в него строку:")
        print("BOT_TOKEN=ваш_токен_здесь")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
        
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add_task", add_task))
    application.add_handler(CommandHandler("list_tasks", list_tasks))
    application.add_handler(CommandHandler("complete_task", complete_task))
    application.add_handler(CommandHandler("delete_task", delete_task))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен и готов к работе!")
    application.run_pollinxg(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
