import sqlite3
from datetime import datetime
from config import DB_FILE

def init_db():
    # Создает таблицы в БД
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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS late_employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee TEXT NOT NULL,
            employee_name TEXT,
            late_time TEXT,
            date TEXT NOT NULL,
            message_text TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

def execute_db(query, params=None, fetch=False):
    # Выполняет запрос к БД
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchall() if fetch else None
        conn.commit()
        return result
    finally:
        conn.close()

# Функции для задач
def load_tasks():
    rows = execute_db("SELECT id, task, deadline, employee, completed, created_at FROM tasks", fetch=True)
    return [{
        "id": row[0],
        "task": row[1],
        "deadline": row[2],
        "employee": row[3],
        "completed": bool(row[4]),
        "created_at": row[5]
    } for row in rows] if rows else []

def insert_task(task, deadline, employee, created_at):
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
        execute_db(query, params)

def delete_task_by_id(task_id):
    execute_db("DELETE FROM tasks WHERE id = ?", (task_id,))

# Функции для опозданий
def insert_late_employee(employee, employee_name=None, late_time=None, message_text=None, created_by=None):
    date = datetime.now().strftime("%d.%m.%Y")
    created_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO late_employees (employee, employee_name, late_time, date, message_text, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (employee, employee_name, late_time, date, message_text, created_by, created_at))
    conn.commit()
    conn.close()

def load_late_employees(date=None, employee=None):
    query = "SELECT id, employee, employee_name, late_time, date, message_text, created_by, created_at FROM late_employees WHERE 1=1"
    params = []
    
    if date:
        query += " AND date = ?"
        params.append(date)
    
    if employee:
        query += " AND employee = ?"
        params.append(employee)
    
    query += " ORDER BY date DESC, created_at DESC"
    rows = execute_db(query, params, fetch=True)
    
    if not rows:
        return []
    
    return [{
        "id": row[0],
        "employee": row[1],
        "employee_name": row[2],
        "late_time": row[3],
        "date": row[4],
        "message_text": row[5],
        "created_by": row[6],
        "created_at": row[7]
    } for row in rows]
