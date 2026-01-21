from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_keyboard(buttons):
    # Создает клавиатуру из списка кнопок
    # buttons: [[("Текст", "callback_data"), ...], ...]
    keyboard = []
    for row in buttons:
        keyboard_row = []
        for button_text, callback_data in row:
            keyboard_row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        keyboard.append(keyboard_row)
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard():
    buttons = [
        [("➕ Добавить задание", "add_task")],
        [("📋 Все задания", "list_all")],
        [("🟢 Активные", "list_active")],
        [("✅ Выполненные", "list_done")],
        [("⏰ Просроченные", "list_overdue")],
        [("🚶 Назначить опоздавшего", "add_late")],
        [("📝 Список опоздавших", "list_late")],
        [("❓ Помощь", "help")]
    ]
    return create_keyboard(buttons)

def get_list_filter_keyboard():
    buttons = [
        [("📋 Все задания", "list_all")],
        [("🟢 Активные", "list_active")],
        [("✅ Выполненные", "list_done")],
        [("⏰ Просроченные", "list_overdue")],
        [("◀️ Главное меню", "main_menu")]
    ]
    return create_keyboard(buttons)

def get_back_menu_keyboard():
    buttons = [[("◀️ Главное меню", "main_menu")]]
    return create_keyboard(buttons)
