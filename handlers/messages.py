from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
from core.database import insert_task, insert_late_employee
from core.utils import parse_task_message, parse_late_message, normalize_username, parse_date
from ui.keyboards import get_main_menu_keyboard
from core.config import ADD_TASK_INSTRUCTIONS

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    
    # Проверяем, ожидаем ли информацию об опоздании
    if context.user_data.get('waiting_for_late'):
        await handle_late_message(update, context, text)
        return
    
    # Обработка задания
    await handle_task_message(update, context, text)

async def handle_late_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    context.user_data['waiting_for_late'] = False
    
    employee, employee_name, late_time, date = parse_late_message(text, update.message.entities or [])
    employee = normalize_username(employee) if employee else None
    
    if not employee:
        await update.message.reply_text(
            "Ошибка! Укажите сотрудника (имя или @username).\n"
            "Попробуйте снова или вернитесь в главное меню.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Если дата не указана, используем сегодня
    if not date:
        date = datetime.now().strftime("%d.%m.%Y")
    else:
        date_formatted = parse_date(date)
        if not date_formatted:
            await update.message.reply_text(
                "Неверный формат даты! Используйте ДД.ММ.ГГГГ или ДД.ММ.ГГ\n"
                "Попробуйте снова.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        date = date_formatted
    
    # Сохраняем опоздание
    created_by = f"@{update.message.from_user.username}" if update.message.from_user.username else update.message.from_user.first_name
    insert_late_employee(
        employee=employee,
        employee_name=employee_name,
        late_time=late_time if late_time else None,
        message_text=text,
        created_by=created_by
    )
    
    time_info = f"\nВремя опоздания: {late_time}" if late_time else ""
    await update.message.reply_text(
        f"✅ Опоздание зафиксировано!\n\n"
        f"Сотрудник: {employee}\n"
        f"Дата: {date}{time_info}",
        reply_markup=get_main_menu_keyboard()
    )

async def handle_task_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    # Убираем команду если есть
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
    
    task_desc, deadline, employee = parse_task_message(text, update.message.entities)
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
