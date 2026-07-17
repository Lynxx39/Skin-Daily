import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skindaily.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,
        name TEXT NOT NULL,
        ingredients TEXT,
        opened_at TEXT, -- YYYY-MM-DD
        pao_months INTEGER
    )
    """)
    
    # Create routine_steps table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS routine_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        routine_type TEXT NOT NULL, -- AM or PM
        step_order INTEGER NOT NULL,
        frequency_notes TEXT, -- e.g., "2-3x per minggu", "setiap hari", etc.
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    )
    """)
    
    # Add frequency_notes column if it doesn't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE routine_steps ADD COLUMN frequency_notes TEXT")
    except:
        pass  # Column already exists
    
    # Create routine_logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS routine_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL, -- COMPLETED or SKIPPED
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    )
    """)
    
    # Create settings table for Telegram configurations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    conn.commit()
    conn.close()

# Product helpers
def add_product(brand: str, name: str, ingredients: str = None, opened_at: str = None, pao_months: int = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO products (brand, name, ingredients, opened_at, pao_months)
    VALUES (?, ?, ?, ?, ?)
    """, (brand, name, ingredients, opened_at, pao_months))
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return product_id

def get_all_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY brand, name")
    rows = cursor.fetchall()
    products = [dict(row) for row in rows]
    conn.close()
    return products

def get_product(product_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    product = dict(row) if row else None
    conn.close()
    return product

def update_product(product_id: int, brand: str, name: str, ingredients: str = None, opened_at: str = None, pao_months: int = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE products
    SET brand = ?, name = ?, ingredients = ?, opened_at = ?, pao_months = ?
    WHERE id = ?
    """, (brand, name, ingredients, opened_at, pao_months, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    cursor.execute("DELETE FROM routine_steps WHERE product_id = ?", (product_id,))
    cursor.execute("DELETE FROM routine_logs WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()

# Routine helpers
def get_routine(routine_type: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT rs.id as step_id, rs.step_order, rs.frequency_notes, p.*
    FROM routine_steps rs
    JOIN products p ON rs.product_id = p.id
    WHERE rs.routine_type = ?
    ORDER BY rs.step_order
    """, (routine_type,))
    rows = cursor.fetchall()
    steps = [dict(row) for row in rows]
    conn.close()
    return steps

def save_routine_steps(routine_type: str, product_ids: list):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First, clear existing steps for this routine type
    cursor.execute("DELETE FROM routine_steps WHERE routine_type = ?", (routine_type,))
    
    # Insert new steps
    for order, p_id in enumerate(product_ids, start=1):
        # Handle both simple int and dict with notes
        product_id = p_id if isinstance(p_id, int) else p_id.get('id')
        frequency_notes = None if isinstance(p_id, int) else p_id.get('frequency_notes')
        
        cursor.execute("""
        INSERT INTO routine_steps (product_id, routine_type, step_order, frequency_notes)
        VALUES (?, ?, ?, ?)
        """, (product_id, routine_type, order, frequency_notes))
        
    conn.commit()
    conn.close()

def add_routine_log(product_id: int, status: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO routine_logs (product_id, status)
    VALUES (?, ?)
    """, (product_id, status))
    conn.commit()
    conn.close()

def get_recent_logs(limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT rl.*, p.brand, p.name
    FROM routine_logs rl
    JOIN products p ON rl.product_id = p.id
    ORDER BY rl.logged_at DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    logs = [dict(row) for row in rows]
    conn.close()
    return logs

# Settings helpers
def get_setting(key: str, default: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    val = row[0] if row else default
    conn.close()
    return val

def set_setting(key: str, value: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO settings (key, value)
    VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()
    conn.close()
