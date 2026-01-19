import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv()

DB_FILE = "tasks.db"

def init_db():
    """Создает таблицу tasks, если она не существует"""
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

def load_tasks():
    """Загружает все задания из базы данных"""
    init_db()  # Убеждаемся, что таблица существует
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, task, deadline, employee, completed, created_at FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    
    tasks = []
    for row in rows:
        tasks.append({
            "id": row[0],
            "task": row[1],
            "deadline": row[2],
            "employee": row[3],
            "completed": bool(row[4]),  # Конвертируем INTEGER в bool
            "created_at": row[5]
        })
    return tasks

def insert_task(task, deadline, employee, created_at):
    """Добавляет новое задание в базу данных"""
    init_db()
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
    """Обновляет задание в базе данных"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
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
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()

def delete_task_by_id(task_id):
    """Удаляет задание из базы данных по ID"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

def save_tasks(tasks):
    """Совместимость: сохраняет список заданий (используется для полной перезаписи)"""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Удаляем все существующие задачи
    cursor.execute("DELETE FROM tasks")
    
    # Вставляем новые задачи
    for task in tasks:
        cursor.execute("""
            INSERT INTO tasks (id, task, deadline, employee, completed, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task["id"],
            task["task"],
            task["deadline"],
            task["employee"],
            1 if task["completed"] else 0,
            task["created_at"]
        ))
    
    conn.commit()
    conn.close()

def normalize_username(username):
    """Нормализует username - добавляет @ если нужно"""
    if not username or username == "Не указан" or username.startswith("@"):
        return username
    if username.replace("_", "").replace("-", "").isalnum():
        return f"@{username}"
    return username

def parse_date(date_str):
    """Парсит дату в формате ДД.ММ.ГГГГ или ДД.ММ.ГГ"""
    for fmt in ["%d.%m.%Y", "%d.%m.%y"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue
    return None

def deadline_to_datetime(deadline_str):
    """Конвертирует строку дедлайна в datetime для сортировки"""
    for fmt in ["%d.%m.%Y", "%d.%m.%y"]:
        try:
            return datetime.strptime(deadline_str, fmt)
        except ValueError:
            continue
    return datetime.max

def is_overdue(task):
    """Проверяет, просрочено ли задание"""
    if task["completed"]:
        return False
    deadline_date = deadline_to_datetime(task["deadline"])
    return deadline_date.date() < datetime.now().date()

def get_task_status(task):
    """Возвращает статус задания с эмодзи"""
    if task["completed"]:
        return "✅ Completed"
    elif is_overdue(task):
        return "⏰ Overdue"
    else:
        return "🟢 In progress"

def get_main_menu_keyboard():
    """Создает клавиатуру главного меню"""
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
    """Создает клавиатуру для фильтрации заданий"""
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
    keyboard = get_main_menu_keyboard()
    await update.message.reply_text(
        "Привет! Я бот для управления заданиями.\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = get_main_menu_keyboard()
    if update.message:
        await update.message.reply_text(
            "Привет! Я бот для управления заданиями.\n\n"
            "Доступные команды:\n"
            "/start или /menu - Главное меню\n"
            "/add_task - Добавить новое задание\n"
            "/list_tasks - Показать все задания\n\n"
            "Выберите действие:",
            reply_markup=keyboard
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "Привет! Я бот для управления заданиями.\n\n"
            "Доступные команды:\n"
            "/start или /menu - Главное меню\n"
            "/add_task - Добавить новое задание\n"
            "/list_tasks - Показать все задания\n\n"
            "Выберите действие:",
            reply_markup=keyboard
        )
        await update.callback_query.answer()

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    if text.startswith("/add_task"):
        text = text.replace("/add_task", "").strip()
    
    # Проверка totally все равно к регистру
    text_lower = text.lower()
    if "задание:" not in text_lower or "дедлайн:" not in text_lower:
        await update.message.reply_text(
            "Не понимаю это сообщение. Используйте команды:\n"
            "/add_task - чтобы узнать, как добавить задание\n"
            "/list_tasks - чтобы посмотреть все задания"
        )
        return
    
    # Парсим сообщение построчно (все равно к регистру)
    task_desc = ""
    deadline = ""
    employee = ""
    
    for line in text.split('\n'):
        line = line.strip()
        line_lower = line.lower()
        if line_lower.startswith("задание:"):
            # Находим позицию ":" и берем текст после неё
            idx = line.find(":") + 1
            task_desc = line[idx:].strip()
        elif line_lower.startswith("дедлайн:"):
            idx = line.find(":") + 1
            deadline = line[idx:].strip()
        elif line_lower.startswith("сотрудник:"):
            idx = line.find(":") + 1
            employee = line[idx:].strip()
    
    # Ищем упоминания пользователей
    if not employee and update.message.entities:
        for entity in update.message.entities:
            if entity.type == "mention":
                employee = text[entity.offset:entity.offset + entity.length]
                break
            elif entity.type == "text_mention" and entity.user:
                employee = f"@{entity.user.username}" if entity.user.username else f"{entity.user.first_name}"
                break
    
    employee = normalize_username(employee) if employee else "Не указан"
    
    if not task_desc or not deadline:
        await update.message.reply_text("Ошибка! Укажите задание и дедлайн.")
        return
    
    # Парсим дату
    deadline_formatted = parse_date(deadline)
    if not deadline_formatted:
        await update.message.reply_text(
            "Неверный формат даты! Используйте:\n"
            "• ДД.ММ.ГГГГ (например, 10.01.2026)\n"
            "• ДД.ММ.ГГ (например, 10.01.26)"
        )
        return
    
    # Сохраняем задание
    created_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    task_id = insert_task(task_desc, deadline_formatted, employee, created_at)
    
    keyboard = get_main_menu_keyboard()
    await update.message.reply_text(
        f"Задание добавлено!\n\n"
        f"Задание: {task_desc}\n"
        f"Дедлайн: {deadline_formatted}\n"
        f"Сотрудник: {employee}",
        reply_markup=keyboard
    )

async def show_list_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает кнопки фильтрации заданий"""
    keyboard = get_list_filter_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Выберите категорию заданий:",
            reply_markup=keyboard
        )
    elif update.message:
        await update.message.reply_text(
            "Выберите категорию заданий:",
            reply_markup=keyboard
        )

def format_tasks_list(tasks, show_buttons=True):
    """Форматирует список заданий с кнопками управления"""
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
                    f"✅ Выполнить", 
                    callback_data=f"complete_{task['id']}"
                ))
            task_buttons.append(InlineKeyboardButton(
                f"🗑️ Удалить", 
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
    """Команда /list_tasks - показывает кнопки фильтра"""
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
        keyboard = get_main_menu_keyboard()
        await update.message.reply_text(f"Задание #{task_id} удалено!", reply_markup=keyboard)
    except ValueError:
        await update.message.reply_text("ID должен быть числом!")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех callback-запросов от кнопок"""
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    data = query.data
    
    # Главное меню
    if data == "main_menu":
        keyboard = get_main_menu_keyboard()
        await query.edit_message_text(
            "Привет! Я бот для управления заданиями.\n\n"
            "Выберите действие:",
            reply_markup=keyboard
        )
    
    # Помощь
    elif data == "help":
        keyboard = get_main_menu_keyboard()
        await query.edit_message_text(
            "Привет! Я бот для управления заданиями.\n\n"
            "Доступные команды:\n"
            "/start или /menu - Главное меню\n"
            "/add_task - Добавить новое задание\n"
            "/list_tasks - Показать все задания\n\n"
            "Выберите действие:",
            reply_markup=keyboard
        )
    
    # Добавить задание
    elif data == "add_task":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")
        ]])
        await query.edit_message_text(
            "Чтобы добавить задание, отправьте сообщение в формате:\n\n"
            "Задание: [описание задания]\n"
            "Дедлайн: [дата: ДД.ММ.ГГГГ или ДД.ММ.ГГ]\n"
            "Сотрудник: @username или имя\n\n"
            "Пример:\n"
            "Задание: Подготовить отчет\n"
            "Дедлайн: 25.12.2024\n"
            "Сотрудник: @ivan_petrov\n\n"
            "Можно использовать короткий формат даты: 10.01.26\n"
            "Можно упомянуть сотрудника через @username прямо в сообщении!",
            reply_markup=keyboard
        )
    
    # Список заданий - фильтрация
    elif data == "list_all":
        tasks = load_tasks()
        message, keyboard = format_tasks_list(tasks)
        if message:
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            keyboard = get_list_filter_keyboard()
            await query.edit_message_text("Список заданий пуст.", reply_markup=keyboard)
    
    elif data == "list_active":
        tasks = [t for t in load_tasks() if not t["completed"]]
        message, keyboard = format_tasks_list(tasks)
        if message:
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            keyboard = get_list_filter_keyboard()
            await query.edit_message_text("Активных заданий нет.", reply_markup=keyboard)
    
    elif data == "list_done":
        tasks = [t for t in load_tasks() if t["completed"]]
        message, keyboard = format_tasks_list(tasks)
        if message:
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            keyboard = get_list_filter_keyboard()
            await query.edit_message_text("Выполненных заданий нет.", reply_markup=keyboard)
    
    elif data == "list_overdue":
        tasks = [t for t in load_tasks() if is_overdue(t)]
        message, keyboard = format_tasks_list(tasks)
        if message:
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            keyboard = get_list_filter_keyboard()
            await query.edit_message_text("Просроченных заданий нет.", reply_markup=keyboard)
    
    # Выполнить задание
    elif data.startswith("complete_"):
        task_id = int(data.split("_")[1])
        tasks = load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if task:
            update_task(task_id, completed=True)
            await query.answer(f"Задание #{task_id} отмечено как выполненное!")
            
            # Обновляем список заданий
            current_filter = "list_all"  # Можно улучшить, сохраняя последний фильтр
            tasks = load_tasks()
            message, keyboard = format_tasks_list(tasks)
            if message:
                await query.edit_message_text(message, reply_markup=keyboard)
        else:
            await query.answer("Задание не найдено!")
    
    # Удалить задание
    elif data.startswith("delete_"):
        task_id = int(data.split("_")[1])
        delete_task_by_id(task_id)
        await query.answer(f"Задание #{task_id} удалено!")
        
        # Обновляем список заданий
        tasks = load_tasks()
        message, keyboard = format_tasks_list(tasks)
        if message:
            await query.edit_message_text(message, reply_markup=keyboard)
        else:
            keyboard = get_list_filter_keyboard()
            await query.edit_message_text("Список заданий пуст.", reply_markup=keyboard)

def main():
    # Инициализируем базу данных при запуске
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
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()