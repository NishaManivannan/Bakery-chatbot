import sqlite3

DB_NAME = "orders.db"

def create_table():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            category TEXT,
            flavor TEXT,
            topping TEXT,
            size TEXT,
            customization TEXT,
            cost INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def insert_order(name, phone, category, flavor, topping, size, customization, cost):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (name, phone, category, flavor, topping, size, customization, cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, phone, category, flavor, topping, size, customization, cost))
    conn.commit()
    conn.close()

def delete_order_by_name_phone(name, phone):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM orders WHERE name = ? AND phone = ?', (name, phone))
    conn.commit()
    conn.close()

def order_exists(name, phone):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id FROM orders WHERE name = ? AND phone = ?', (name, phone))
    result = c.fetchone()
    conn.close()
    return result is not None
