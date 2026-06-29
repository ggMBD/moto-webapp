"""
db.py — Database connection, initialisation, helpers
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
    return [dict(r) for r in cursor_result]

def next_invoice_number(conn, table, prefix):
    row = conn.execute(
        f"""SELECT invoice_number FROM {table}
            WHERE invoice_number LIKE ?
            ORDER BY id DESC LIMIT 1""",
        (f"{prefix}-%",)
    ).fetchone()
    if row and row["invoice_number"]:
        try:
            last_n = int(row["invoice_number"].split("-")[-1])
        except ValueError:
            last_n = 0
    else:
        last_n = 0
    return f"{prefix}-{last_n + 1:04d}"

def init_db():
    with get_db() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                full_name  TEXT DEFAULT '',
                role       TEXT DEFAULT 'staff',
                is_active  INTEGER DEFAULT 1,
                permissions TEXT DEFAULT '{}',
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
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number  TEXT UNIQUE,
                customer_id     INTEGER,
                user_id         INTEGER,
                total           REAL DEFAULT 0,
                discount        REAL DEFAULT 0,
                payment_method  TEXT DEFAULT 'cash',
                payment_status  TEXT DEFAULT 'paid',
                amount_paid     REAL DEFAULT 0,
                note            TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now')),
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
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number  TEXT,
                supplier_id     INTEGER,
                product_id      INTEGER NOT NULL,
                user_id         INTEGER,
                qty             INTEGER NOT NULL,
                unit_price      REAL DEFAULT 0,
                total           REAL DEFAULT 0,
                note            TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now')),
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
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number  TEXT UNIQUE,
                customer_id     INTEGER,
                bike_id         INTEGER,
                user_id         INTEGER,
                vehicle         TEXT DEFAULT '',
                description     TEXT DEFAULT '',
                status          TEXT DEFAULT 'pending',
                labor_cost      REAL DEFAULT 0,
                parts_cost      REAL DEFAULT 0,
                discount        REAL DEFAULT 0,
                total           REAL DEFAULT 0,
                payment_method  TEXT DEFAULT 'cash',
                payment_status  TEXT DEFAULT 'unpaid',
                amount_paid     REAL DEFAULT 0,
                note            TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now')),
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
            CREATE TABLE IF NOT EXISTS repair_labor (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                repair_id  INTEGER NOT NULL,
                description TEXT NOT NULL,
                price      REAL NOT NULL,
                FOREIGN KEY(repair_id) REFERENCES repairs(id)
            );
        """)
        # Add missing columns if upgrading from v4
        try:
            c.execute("ALTER TABLE repairs ADD COLUMN discount REAL DEFAULT 0")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT '{}'")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE purchases ADD COLUMN invoice_number TEXT")
        except Exception:
            pass

        # Seed default admin
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            c.execute(
                "INSERT INTO users (username,password,full_name,role,is_active) VALUES (?,?,?,?,?)",
                ("admin", generate_password_hash("admin123"), "Administrator", "admin", 1)
            )
            print("\n  👤  Default admin — username: admin  password: admin123")
            print("      ⚠️   Change password after first login!\n")
