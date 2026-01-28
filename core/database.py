import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import time
from core.config import (
    DB_FILE, USE_POSTGRES, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
)

def get_connection():
    """Возвращает соединение с БД (PostgreSQL или SQLite)"""
    if USE_POSTGRES:
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    else:
        return sqlite3.connect(DB_FILE)

def wait_for_postgres(max_retries=30, delay=2):
    """Ожидает готовности PostgreSQL (для Docker)"""
    if not USE_POSTGRES:
        return True
    
    for i in range(max_retries):
        try:
            conn = get_connection()
            conn.close()
            print("PostgreSQL готов к работе!")
            return True
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            if i < max_retries - 1:
                print(f"Ожидание PostgreSQL... (попытка {i+1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"Не удалось подключиться к PostgreSQL: {e}")
                return False
    return False

def init_db():
    """Создает таблицы в БД"""
    # Ждем готовности PostgreSQL, если используется
    if USE_POSTGRES:
        if not wait_for_postgres():
            raise Exception("Не удалось подключиться к PostgreSQL")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        # PostgreSQL схемы
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                task TEXT NOT NULL,
                deadline TEXT NOT NULL,
                employee TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS late_employees (
                id SERIAL PRIMARY KEY,
                employee TEXT NOT NULL,
                employee_name TEXT,
                late_time TEXT,
                date TEXT NOT NULL,
                message_text TEXT,
                created_by TEXT,
                created_at TEXT NOT NULL
            )
        """)
    else:
        # SQLite схемы (для обратной совместимости)
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
    """Выполняет запрос к БД"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch:
            if USE_POSTGRES:
                # Для PostgreSQL возвращаем словари
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                result = cursor.fetchall()
                return [dict(row) for row in result]
            else:
                result = cursor.fetchall()
                return result
        else:
            conn.commit()
            return None
    finally:
        conn.close()

# Функции для задач
def load_tasks():
    """Загружает все задачи из БД"""
    rows = execute_db("SELECT id, task, deadline, employee, completed, created_at FROM tasks", fetch=True)
    
    if USE_POSTGRES:
        return [{
            "id": row["id"],
            "task": row["task"],
            "deadline": row["deadline"],
            "employee": row["employee"],
            "completed": bool(row["completed"]),
            "created_at": row["created_at"]
        } for row in rows] if rows else []
    else:
        return [{
            "id": row[0],
            "task": row[1],
            "deadline": row[2],
            "employee": row[3],
            "completed": bool(row[4]),
            "created_at": row[5]
        } for row in rows] if rows else []

def insert_task(task, deadline, employee, created_at):
    """Добавляет новую задачу в БД"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute("""
            INSERT INTO tasks (task, deadline, employee, completed, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (task, deadline, employee, 0, created_at))
        task_id = cursor.fetchone()[0]
    else:
        cursor.execute("""
            INSERT INTO tasks (task, deadline, employee, completed, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (task, deadline, employee, 0, created_at))
        task_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return task_id

def update_task(task_id, completed=None, task=None, deadline=None, employee=None):
    """Обновляет задачу в БД"""
    updates = []
    params = []
    
    if completed is not None:
        updates.append("completed = %s" if USE_POSTGRES else "completed = ?")
        params.append(1 if completed else 0)
    if task is not None:
        updates.append("task = %s" if USE_POSTGRES else "task = ?")
        params.append(task)
    if deadline is not None:
        updates.append("deadline = %s" if USE_POSTGRES else "deadline = ?")
        params.append(deadline)
    if employee is not None:
        updates.append("employee = %s" if USE_POSTGRES else "employee = ?")
        params.append(employee)
    
    if updates:
        params.append(task_id)
        placeholder = "%s" if USE_POSTGRES else "?"
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = {placeholder}"
        execute_db(query, params)

def delete_task_by_id(task_id):
    """Удаляет задачу по ID"""
    execute_db("DELETE FROM tasks WHERE id = %s" if USE_POSTGRES else "DELETE FROM tasks WHERE id = ?", (task_id,))

# Функции для опозданий
def insert_late_employee(employee, employee_name=None, late_time=None, message_text=None, created_by=None):
    """Добавляет запись об опоздании сотрудника"""
    date = datetime.now().strftime("%d.%m.%Y")
    created_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute("""
            INSERT INTO late_employees (employee, employee_name, late_time, date, message_text, created_by, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (employee, employee_name, late_time, date, message_text, created_by, created_at))
    else:
        cursor.execute("""
            INSERT INTO late_employees (employee, employee_name, late_time, date, message_text, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (employee, employee_name, late_time, date, message_text, created_by, created_at))
    
    conn.commit()
    conn.close()

def load_late_employees(date=None, employee=None):
    """Загружает записи об опозданиях"""
    query = "SELECT id, employee, employee_name, late_time, date, message_text, created_by, created_at FROM late_employees WHERE 1=1"
    params = []
    
    if date:
        query += " AND date = %s" if USE_POSTGRES else " AND date = ?"
        params.append(date)
    
    if employee:
        query += " AND employee = %s" if USE_POSTGRES else " AND employee = ?"
        params.append(employee)
    
    query += " ORDER BY date DESC, created_at DESC"
    rows = execute_db(query, params, fetch=True)
    
    if not rows:
        return []
    
    if USE_POSTGRES:
        return [{
            "id": row["id"],
            "employee": row["employee"],
            "employee_name": row["employee_name"],
            "late_time": row["late_time"],
            "date": row["date"],
            "message_text": row["message_text"],
            "created_by": row["created_by"],
            "created_at": row["created_at"]
        } for row in rows]
    else:
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
