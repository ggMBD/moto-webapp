"""
db.py — Database connection, initialisation, helpers
Shared by all route blueprints
"""
import sqlite3, os
from contextlib import contextmanager
from werkzeug.security import generate_password_hash

DB_FILE = os.environ.get("DB_FILE", os.path.join(os.path.dirname(__file__), "motoshop.db"))

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def rows(cursor_result):
    """Convert sqlite rows to list of dicts."""
    return [dict(r) for r in cursor_result]

def init_db():
    with get_db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                full_name  TEXT DEFAULT '',
                role       TEXT DEFAULT 'staff',
                created_at TEXT DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS products (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ref        TEXT UNIQUE NOT NULL,
                name       TEXT NOT NULL,
                category   TEXT DEFAULT '',
                brand      TEXT DEFAULT '',
                qty        INTEGER DEFAULT 0,
                buy_price  REAL DEFAULT 0,
                sell_price REAL DEFAULT 0,
                min_stock  INTEGER DEFAULT 5,
                created_at TEXT DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS customers (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                cin        TEXT DEFAULT '',
                phone      TEXT DEFAULT '',
                email      TEXT DEFAULT '',
                address    TEXT DEFAULT '',
                ts         REAL DEFAULT 0,
                created_at TEXT DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS suppliers (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                phone      TEXT DEFAULT '',
                email      TEXT DEFAULT '',
                address    TEXT DEFAULT '',
                notes      TEXT DEFAULT '',
                created_at TEXT DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS sales (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                user_id     INTEGER,
                total       REAL DEFAULT 0,
                discount    REAL DEFAULT 0,
                note        TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(customer_id) REFERENCES customers(id),
                FOREIGN KEY(user_id)     REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS sale_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id    INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                qty        INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY(sale_id)    REFERENCES sales(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            CREATE TABLE IF NOT EXISTS purchases (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER,
                product_id  INTEGER NOT NULL,
                user_id     INTEGER,
                qty         INTEGER NOT NULL,
                unit_price  REAL DEFAULT 0,
                total       REAL DEFAULT 0,
                note        TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
                FOREIGN KEY(product_id)  REFERENCES products(id),
                FOREIGN KEY(user_id)     REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS bikes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id      INTEGER NOT NULL,
                brand         TEXT DEFAULT '',
                model         TEXT DEFAULT '',
                year          INTEGER,
                plate         TEXT DEFAULT '',
                vin           TEXT DEFAULT '',
                color         TEXT DEFAULT '',
                mileage       INTEGER DEFAULT 0,
                note          TEXT DEFAULT '',
                created_at    TEXT DEFAULT (date('now')),
                updated_at    TEXT DEFAULT (date('now')),
                FOREIGN KEY(owner_id) REFERENCES customers(id)
            );
            CREATE TABLE IF NOT EXISTS repairs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                bike_id     INTEGER,
                user_id     INTEGER,
                vehicle     TEXT DEFAULT '',
                description TEXT DEFAULT '',
                status      TEXT DEFAULT 'pending',
                labor_cost  REAL DEFAULT 0,
                parts_cost  REAL DEFAULT 0,
                total       REAL DEFAULT 0,
                note        TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(customer_id) REFERENCES customers(id),
                FOREIGN KEY(bike_id)     REFERENCES bikes(id),
                FOREIGN KEY(user_id)     REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS repair_parts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                repair_id  INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                qty        INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY(repair_id)  REFERENCES repairs(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
        """)
        # Seed default admin
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            c.execute(
                "INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
                ("admin", generate_password_hash("admin123"), "Administrator", "admin")
            )
            print("\n  👤  Default admin — username: admin  password: admin123")
            print("      ⚠️   Change password after first login!\n")
