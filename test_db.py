# Тестовый скрипт для проверки работы SQLite базы данных
import sqlite3
import os
import sys
from datetime import datetime

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Импортируем функции из main.py
from main import (
    init_db, load_tasks, insert_task, update_task, 
    delete_task_by_id, DB_FILE
)
    
def test_database():
    # Тестирует все функции базы данных
    print("=" * 50)
    print("ТЕСТИРОВАНИЕ БАЗЫ ДАННЫХ SQLite")
    print("=" * 50)
    
    # Удаляем старую базу данных для чистого теста
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"✓ Удалена старая база данных: {DB_FILE}")
    
    # Тест 1: Инициализация базы данных
    print("\n[Тест 1] Инициализация базы данных...")
    try:
        init_db()
        print("✓ База данных успешно инициализирована")
        
        # Проверяем, что таблица создана
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        table_exists = cursor.fetchone()
        conn.close()
        
        if table_exists:
            print("✓ Таблица 'tasks' успешно создана")
        else:
            print("✗ ОШИБКА: Таблица 'tasks' не найдена!")
            return False
    except Exception as e:
        print(f"✗ ОШИБКА при инициализации: {e}")
        return False
    
    # Тест 2: Загрузка пустого списка
    print("\n[Тест 2] Загрузка пустого списка задач...")
    try:
        tasks = load_tasks()
        if tasks == []:
            print("✓ Пустой список загружен корректно")
        else:
            print(f"✗ ОШИБКА: Ожидался пустой список, получено: {tasks}")
            return False
    except Exception as e:
        print(f"✗ ОШИБКА при загрузке: {e}")
        return False
    
    # Тест 3: Добавление задачи
    print("\n[Тест 3] Добавление новой задачи...")
    try:
        created_at = datetime.now().strftime("%d.%m.%Y %H:%M")
        task_id = insert_task(
            "Тестовое задание",
            "25.12.2024",
            "@test_user",
            created_at
        )
        if task_id and task_id > 0:
            print(f"✓ Задача успешно добавлена с ID: {task_id}")
        else:
            print(f"✗ ОШИБКА: Неверный ID задачи: {task_id}")
            return False
    except Exception as e:
        print(f"✗ ОШИБКА при добавлении задачи: {e}")
        return False
    
    # Тест 4: Загрузка задач
    print("\n[Тест 4] Загрузка задач из базы...")
    try:
        tasks = load_tasks()
        if len(tasks) == 1:
            task = tasks[0]
            if (task["id"] == task_id and 
                task["task"] == "Тестовое задание" and
                task["deadline"] == "25.12.2024" and
                task["employee"] == "@test_user" and
                task["completed"] == False):
                print("✓ Задача успешно загружена со всеми полями")
                print(f"  ID: {task['id']}")
                print(f"  Задание: {task['task']}")
                print(f"  Дедлайн: {task['deadline']}")
                print(f"  Сотрудник: {task['employee']}")
                print(f"  Выполнено: {task['completed']}")
                print(f"  Создано: {task['created_at']}")
            else:
                print(f"✗ ОШИБКА: Неверные данные задачи: {task}")
                return False
        else:
            print(f"✗ ОШИБКА: Ожидалась 1 задача, получено: {len(tasks)}")
            return False
    except Exception as e:
        print(f"✗ ОШИБКА при загрузке задач: {e}")
        return False
    
    # Тест 5: Обновление задачи (отметить как выполненную)
    print("\n[Тест 5] Обновление задачи (отметить как выполненную)...")
    try:
        update_task(task_id, completed=True)
        tasks = load_tasks()
        if tasks[0]["completed"] == True:
            print("✓ Задача успешно обновлена (completed = True)")
        else:
            print(f"✗ ОШИБКА: Задача не обновлена: {tasks[0]}")
            return False
    except Exception as e:
        print(f"✗ ОШИБКА при обновлении задачи: {e}")
        return False
    
    # Тест 6: Добавление еще нескольких задач
    print("\n[Тест 6] Добавление дополнительных задач...")
    try:
        task_id2 = insert_task("Вторая задача", "26.12.2024", "@user2", created_at)
        task_id3 = insert_task("Третья задача", "27.12.2024", "@user3", created_at)
        tasks = load_tasks()
        if len(tasks) == 3:
            print(f"✓ Добавлено еще 2 задачи. Всего задач: {len(tasks)}")
        else:
            print(f"✗ ОШИБКА: Ожидалось 3 задачи, получено: {len(tasks)}")
            return False
    except Exception as e:
        print(f"✗ ОШИБКА при добавлении задач: {e}")
        return False
    
    # Тест 7: Удаление задачи
    print("\n[Тест 7] Удаление задачи...")
    try:
        delete_task_by_id(task_id2)
        tasks = load_tasks()
        if len(tasks) == 2:
            # Проверяем, что удаленная задача не в списке
            task_ids = [t["id"] for t in tasks]
            if task_id2 not in task_ids:
                print(f"✓ Задача с ID {task_id2} успешно удалена")
            else:
                print(f"✗ ОШИБКА: Задача с ID {task_id2} все еще в списке")
                return False
        else:
            print(f"✗ ОШИБКА: Ожидалось 2 задачи, получено: {len(tasks)}")
            return False
    except Exception as e:
        print(f"✗ ОШИБКА при удалении задачи: {e}")
        return False
    
    # Тест 8: Проверка структуры таблицы
    print("\n[Тест 8] Проверка структуры таблицы...")
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(tasks)")
        columns = cursor.fetchall()
        conn.close()
        
        column_names = [col[1] for col in columns]
        required_columns = ['id', 'task', 'deadline', 'employee', 'completed', 'created_at']
        
        missing_columns = [col for col in required_columns if col not in column_names]
        if not missing_columns:
            print("✓ Все необходимые колонки присутствуют:")
            for col in column_names:
                print(f"  - {col}")
        else:
            print(f"✗ ОШИБКА: Отсутствуют колонки: {missing_columns}")
            return False
    except Exception as e:
        print(f"✗ ОШИБКА при проверке структуры: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = test_database()
    if success:
        print("\nБаза данных готова к использованию!")
        print(f"Файл базы данных: {DB_FILE}")
    else:
        print("\n✗ ТЕСТИРОВАНИЕ ЗАВЕРШИЛОСЬ С ОШИБКАМИ!")
        exit(1)

