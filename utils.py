from datetime import datetime
from config import DATE_FORMATS

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

def parse_task_message(text, entities):
    # Парсит сообщение с заданием
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

def parse_late_message(text, entities):
    # Парсит сообщение об опоздании
    employee = ""
    employee_name = ""
    late_time = ""
    date = ""
    
    for line in text.split('\n'):
        line = line.strip()
        line_lower = line.lower()
        if line_lower.startswith("сотрудник:") or line_lower.startswith("имя:"):
            employee = line[line.find(":") + 1:].strip()
        elif line_lower.startswith("время:") or line_lower.startswith("опоздал на:"):
            late_time = line[line.find(":") + 1:].strip()
        elif line_lower.startswith("дата:"):
            date = line[line.find(":") + 1:].strip()
    
    if not employee and entities:
        for entity in entities:
            if entity.type == "mention":
                employee = text[entity.offset:entity.offset + entity.length]
                break
            elif entity.type == "text_mention" and entity.user:
                employee = f"@{entity.user.username}" if entity.user.username else entity.user.first_name
                employee_name = entity.user.first_name
                break
    
    return employee, employee_name, late_time, date

def format_tasks_list(tasks, show_buttons=True):
    # Форматирует список заданий
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
                task_buttons.append(("✅ Выполнить", f"complete_{task['id']}"))
            task_buttons.append(("🗑️ Удалить", f"delete_{task['id']}"))
            keyboard_buttons.append(task_buttons)
    
    if show_buttons:
        keyboard_buttons.append([("◀️ Главное меню", "main_menu")])
        from keyboards import create_keyboard
        keyboard = create_keyboard(keyboard_buttons)
    else:
        keyboard = None
    
    return message, keyboard
