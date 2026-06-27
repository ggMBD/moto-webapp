"""
seed.py — Generate realistic dummy data for Z-MOTO Tunisia
Run: python seed.py
WARNING: This will RESET the database completely.
"""
import sqlite3, os, random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

DB_FILE = os.path.join(os.path.dirname(__file__), "motoshop.db")

# ── Tunisian names ───────────────────────────────────────────
FIRST_NAMES = [
    "Mohamed", "Ahmed", "Ali", "Youssef", "Omar", "Karim", "Bilel", "Amine",
    "Sami", "Rami", "Nizar", "Fares", "Houssem", "Wassim", "Maher", "Slim",
    "Tarek", "Hedi", "Lotfi", "Walid", "Anis", "Mehdi", "Zied", "Aymen",
    "Hichem", "Sofien", "Adel", "Fethi", "Mounir", "Khaled"
]
LAST_NAMES = [
    "Ben Ali", "Ben Salem", "Chaabane", "Trabelsi", "Gharbi", "Jebali",
    "Mansouri", "Bouazizi", "Khelifi", "Hamdi", "Riahi", "Sfaxi",
    "Turki", "Maaloul", "Zouari", "Belhaj", "Oueslati", "Ksouri",
    "Ayari", "Hammami", "Slimani", "Ferchichi", "Abidi", "Laabidi",
    "Ben Youssef", "Cherni", "Nasr", "Dridi", "Hamdouni", "Tlili"
]
CITIES = [
    "Tunis", "Sfax", "Sousse", "Kairouan", "Bizerte", "Gabès",
    "Ariana", "Gafsa", "Monastir", "Ben Arous", "Nabeul", "Manouba",
    "Médenine", "Kasserine", "Beja", "Jendouba", "Mahdia", "Siliana"
]
STREETS = [
    "Rue de la République", "Avenue Habib Bourguiba", "Rue Ibn Khaldoun",
    "Avenue de Carthage", "Rue de Marseille", "Avenue de Paris",
    "Rue Mongi Slim", "Avenue Mohamed V", "Rue Farhat Hached",
    "Avenue de la Liberté", "Rue Sidi Bou Said", "Avenue Tahar Haddad"
]

# ── Moto brands & models in Tunisia ─────────────────────────
MOTO_BRANDS = ["Yamaha", "Honda", "Suzuki", "Kawasaki", "KTM", "Bajaj", "TVS", "Lifan", "Sym", "Kymco"]
MOTO_MODELS = {
    "Yamaha":   ["YBR 125", "MT-07", "R125", "NMAX 155", "FZ-S", "Fazer 150"],
    "Honda":    ["CB 125F", "CB 150R", "CB500F", "CG 125", "XR 150", "PCX 150"],
    "Suzuki":   ["GN 125", "GSX-R 150", "Gixxer 150", "Intruder 150", "Access 125"],
    "Kawasaki": ["Z400", "Ninja 400", "W175", "KLX 150", "Versys 300"],
    "KTM":      ["Duke 125", "Duke 200", "Duke 390", "RC 125", "Adventure 250"],
    "Bajaj":    ["Pulsar NS200", "Pulsar 150", "Avenger 220", "Discover 125"],
    "TVS":      ["Apache RTR 160", "Apache RTR 200", "Star City+", "Radeon"],
    "Lifan":    ["KPR 150", "KPM 200", "LF150-J", "Hunter 200"],
    "Sym":      ["Jet 125", "Wolf 150", "Fighter 150"],
    "Kymco":    ["Agility 125", "Like 150", "People 150"],
}

# ── Parts catalog ────────────────────────────────────────────
PARTS = [
    # (ref, name, category, brand, buy_price, sell_price, min_stock)
    ("FRE-001", "Plaquettes de frein avant",     "Freinage",    "EBC",      18.0,  32.0,  10),
    ("FRE-002", "Plaquettes de frein arrière",   "Freinage",    "EBC",      14.0,  25.0,  10),
    ("FRE-003", "Disque de frein avant 260mm",   "Freinage",    "Braking",  45.0,  80.0,   5),
    ("FRE-004", "Disque de frein arrière 220mm", "Freinage",    "Braking",  38.0,  68.0,   5),
    ("FRE-005", "Câble de frein avant",          "Freinage",    "Generic",   6.0,  12.0,  15),
    ("FRE-006", "Câble de frein arrière",        "Freinage",    "Generic",   5.5,  11.0,  15),
    ("FRE-007", "Maître cylindre frein avant",   "Freinage",    "Nissin",   35.0,  65.0,   3),
    ("MOT-001", "Huile moteur 10W40 1L",         "Lubrification","Motul",    8.5,  15.0,  30),
    ("MOT-002", "Huile moteur 20W50 1L",         "Lubrification","Castrol",  7.0,  13.0,  30),
    ("MOT-003", "Filtre à huile",                "Filtration",  "Generic",   4.5,   9.0,  20),
    ("MOT-004", "Filtre à air",                  "Filtration",  "Generic",   8.0,  16.0,  15),
    ("MOT-005", "Bougie d'allumage NGK CR7HSA",  "Allumage",    "NGK",       4.0,   8.0,  25),
    ("MOT-006", "Bougie d'allumage NGK CR8HSA",  "Allumage",    "NGK",       4.0,   8.0,  20),
    ("MOT-007", "Bougie iridium NGK",            "Allumage",    "NGK",      12.0,  22.0,  10),
    ("MOT-008", "Joint de culasse 125cc",        "Moteur",      "Generic",   9.0,  18.0,   8),
    ("MOT-009", "Segment piston 125cc",          "Moteur",      "Generic",  12.0,  24.0,   6),
    ("MOT-010", "Chaîne de distribution",        "Moteur",      "Generic",  18.0,  35.0,   5),
    ("TRA-001", "Chaîne de transmission 428",    "Transmission","DID",      22.0,  40.0,  10),
    ("TRA-002", "Chaîne de transmission 520",    "Transmission","DID",      28.0,  50.0,   8),
    ("TRA-003", "Kit chaîne + pignons 428",      "Transmission","Generic",  38.0,  70.0,   8),
    ("TRA-004", "Pignon avant 14 dents",         "Transmission","Generic",   8.0,  16.0,  10),
    ("TRA-005", "Couronne arrière 42 dents",     "Transmission","Generic",  18.0,  32.0,   8),
    ("TRA-006", "Câble d'embrayage",             "Transmission","Generic",   6.0,  12.0,  15),
    ("SUS-001", "Amortisseur arrière universel", "Suspension",  "YSS",      55.0, 100.0,   4),
    ("SUS-002", "Huile de fourche 5W 1L",        "Suspension",  "Motul",    12.0,  22.0,  10),
    ("SUS-003", "Joint spi fourche 33mm",        "Suspension",  "Generic",   5.0,  10.0,  10),
    ("SUS-004", "Joint spi fourche 35mm",        "Suspension",  "Generic",   5.5,  11.0,  10),
    ("SUS-005", "Roulement de roue avant",       "Suspension",  "SKF",       8.0,  16.0,  10),
    ("SUS-006", "Roulement de roue arrière",     "Suspension",  "SKF",       8.0,  16.0,  10),
    ("ELE-001", "Batterie 12V 7Ah",              "Électricité", "Yuasa",    28.0,  52.0,   5),
    ("ELE-002", "Batterie 12V 9Ah",              "Électricité", "Yuasa",    35.0,  65.0,   4),
    ("ELE-003", "Relais démarreur",              "Électricité", "Generic",   7.0,  14.0,   8),
    ("ELE-004", "Régulateur de tension",         "Électricité", "Generic",  12.0,  24.0,   5),
    ("ELE-005", "Bobine d'allumage",             "Électricité", "Generic",  18.0,  35.0,   4),
    ("ELE-006", "Ampoule phare H4 60/55W",       "Électricité", "Osram",     4.5,   9.0,  20),
    ("ELE-007", "Ampoule LED H4",                "Électricité", "Generic",  12.0,  22.0,  10),
    ("ELE-008", "Clignotant avant LED",          "Électricité", "Generic",   6.0,  12.0,  12),
    ("ELE-009", "Câble faisceau électrique",     "Électricité", "Generic",  22.0,  42.0,   3),
    ("CAR-001", "Carburateur 125cc complet",     "Carburation", "Generic",  32.0,  60.0,   4),
    ("CAR-002", "Kit joints carburateur",        "Carburation", "Generic",   5.0,  10.0,  15),
    ("CAR-003", "Gicleur principal #108",        "Carburation", "Generic",   2.0,   5.0,  20),
    ("CAR-004", "Gicleur principal #110",        "Carburation", "Generic",   2.0,   5.0,  20),
    ("CAR-005", "Filtre essence inline",         "Carburation", "Generic",   3.5,   7.0,  20),
    ("CAR-006", "Pompe à essence",               "Carburation", "Generic",  18.0,  35.0,   4),
    ("PNE-001", "Pneu avant 80/90-17",           "Pneumatiques","Mitas",    38.0,  68.0,   6),
    ("PNE-002", "Pneu arrière 100/90-17",        "Pneumatiques","Mitas",    45.0,  82.0,   6),
    ("PNE-003", "Pneu avant 90/90-17",           "Pneumatiques","Michelin", 55.0,  95.0,   4),
    ("PNE-004", "Pneu arrière 110/90-17",        "Pneumatiques","Michelin", 62.0, 110.0,   4),
    ("PNE-005", "Chambre à air 2.75-17",         "Pneumatiques","Generic",   5.0,  10.0,  15),
    ("PNE-006", "Chambre à air 3.00-17",         "Pneumatiques","Generic",   5.5,  11.0,  15),
    ("CAR-101", "Carénage avant Yamaha YBR",     "Carrosserie", "Generic",  35.0,  65.0,   3),
    ("CAR-102", "Garde-boue avant universel",    "Carrosserie", "Generic",  12.0,  22.0,   5),
    ("CAR-103", "Rétroviseur gauche universel",  "Carrosserie", "Generic",   8.0,  15.0,  10),
    ("CAR-104", "Rétroviseur droit universel",   "Carrosserie", "Generic",   8.0,  15.0,  10),
    ("CAR-105", "Poignée gauche caoutchouc",     "Carrosserie", "Generic",   4.0,   8.0,  15),
    ("CAR-106", "Poignée droite caoutchouc",     "Carrosserie", "Generic",   4.0,   8.0,  15),
    ("ACC-001", "Antivol U ABUS 55mm",           "Accessoires", "ABUS",     28.0,  52.0,   5),
    ("ACC-002", "Casque intégral M",             "Accessoires", "LS2",      85.0, 150.0,   3),
    ("ACC-003", "Gants moto taille M",           "Accessoires", "Generic",  18.0,  32.0,   5),
    ("ACC-004", "Sacoche de réservoir",          "Accessoires", "Generic",  22.0,  40.0,   4),
    ("ACC-005", "Support téléphone guidon",      "Accessoires", "Generic",  12.0,  22.0,  10),
    ("ACC-006", "Chargeur USB moto",             "Accessoires", "Generic",   8.0,  16.0,  10),
]

# ── Suppliers ────────────────────────────────────────────────
SUPPLIERS = [
    ("Pièces Moto Sfax",       "74 213 456", "contact@pmsfax.tn",      "Av. Bourguiba, Sfax",          "Fournisseur principal pièces détachées"),
    ("Auto Moto Tunis",        "71 889 234", "info@automototunis.tn",   "Rue de la Liberté, Tunis",     "Pièces et accessoires toutes marques"),
    ("SousSou Distribution",   "73 456 789", "sousSou@distrib.tn",      "Zone Industrielle, Sousse",    "Distributeur Yamaha & Honda"),
    ("Importation Ben Salah",  "71 334 567", "bensalah@import.tn",      "Rue Ibn Khaldoun, Ariana",     "Import direct Chine et Europe"),
    ("Moto Accessories Plus",  "72 678 901", "map@moto.tn",             "Centre Commercial, Nabeul",    "Accessoires et équipements"),
    ("ElectroMoto Kairouan",   "77 123 456", "em@kairouan.tn",          "Av. de la République, Kairouan","Pièces électriques spécialisées"),
    ("Pneus & Jantes Bizerte", "72 456 123", "pneus@bizerte.tn",        "Port de Bizerte, Bizerte",     "Pneumatiques import"),
]

# ── Repair descriptions ──────────────────────────────────────
REPAIR_JOBS = [
    ("Vidange + filtre huile",           35.0,  ["MOT-001", "MOT-003"]),
    ("Remplacement plaquettes frein avant", 40.0, ["FRE-001"]),
    ("Remplacement plaquettes frein arrière", 35.0, ["FRE-002"]),
    ("Remplacement bougie",              20.0,  ["MOT-005"]),
    ("Remplacement filtre à air",        20.0,  ["MOT-004"]),
    ("Remplacement chaîne transmission", 50.0,  ["TRA-001"]),
    ("Kit chaîne complet",               60.0,  ["TRA-003"]),
    ("Remplacement batterie",            30.0,  ["ELE-001"]),
    ("Nettoyage carburateur",            45.0,  []),
    ("Réglage carburateur",              30.0,  []),
    ("Remplacement câble embrayage",     25.0,  ["TRA-006"]),
    ("Remplacement amortisseur arrière", 80.0,  ["SUS-001"]),
    ("Remplacement pneu avant",          40.0,  ["PNE-001"]),
    ("Remplacement pneu arrière",        40.0,  ["PNE-002"]),
    ("Révision complète 125cc",         120.0,  ["MOT-001","MOT-003","MOT-004","MOT-005"]),
    ("Diagnostic électrique",            50.0,  []),
    ("Remplacement régulateur tension",  40.0,  ["ELE-004"]),
    ("Remplacement ampoule phare",       15.0,  ["ELE-006"]),
    ("Réparation crevaison",             20.0,  ["PNE-005"]),
    ("Remplacement roulements roue",     55.0,  ["SUS-005","SUS-006"]),
]

REPAIR_STATUSES = ["done","done","done","done","in_progress","pending","waiting_parts","cancelled"]

def random_phone():
    prefix = random.choice(["20","21","22","23","24","25","26","27","28","29",
                             "50","51","52","53","54","55","56","57","58","59",
                             "90","91","92","93","94","95","96","97","98","99"])
    return prefix + str(random.randint(100000, 999999))

def random_name():
    return random.choice(FIRST_NAMES) + " " + random.choice(LAST_NAMES)

def random_address():
    n = random.randint(1, 120)
    return f"{n}, {random.choice(STREETS)}, {random.choice(CITIES)}"

def random_vehicle():
    brand = random.choice(MOTO_BRANDS)
    model = random.choice(MOTO_MODELS[brand])
    year  = random.randint(2015, 2024)
    return f"{brand} {model} {year}"

def rand_date(days_back=365):
    base = datetime.now() - timedelta(days=days_back)
    delta = timedelta(days=random.randint(0, days_back),
                      hours=random.randint(8, 18),
                      minutes=random.randint(0, 59))
    return (base + delta).strftime("%Y-%m-%d %H:%M:%S")

def random_cin(used_cins):
    """Tunisian CIN: 8 digits, unique."""
    while True:
        cin = str(random.randint(10000000, 19999999))
        if cin not in used_cins:
            used_cins.add(cin)
            return cin

def build():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("  🗑  Old database removed")

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # ── Schema ───────────────────────────────────────────────
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            role TEXT DEFAULT 'staff',
            created_at TEXT DEFAULT (date('now'))
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ref TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT DEFAULT '',
            brand TEXT DEFAULT '',
            qty INTEGER DEFAULT 0,
            buy_price REAL DEFAULT 0,
            sell_price REAL DEFAULT 0,
            min_stock INTEGER DEFAULT 5,
            created_at TEXT DEFAULT (date('now'))
        );
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cin TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            address TEXT DEFAULT '',
            ts REAL DEFAULT 0,
            created_at TEXT DEFAULT (date('now'))
        );
        CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            address TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (date('now'))
        );
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            user_id INTEGER,
            total REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES sales(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER,
            product_id INTEGER NOT NULL,
            user_id INTEGER,
            qty INTEGER NOT NULL,
            unit_price REAL DEFAULT 0,
            total REAL DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE bikes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            brand TEXT DEFAULT '',
            model TEXT DEFAULT '',
            year INTEGER,
            plate TEXT DEFAULT '',
            vin TEXT DEFAULT '',
            color TEXT DEFAULT '',
            mileage INTEGER DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (date('now')),
            updated_at TEXT DEFAULT (date('now')),
            FOREIGN KEY(owner_id) REFERENCES customers(id)
        );
        CREATE TABLE repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            bike_id INTEGER,
            user_id INTEGER,
            vehicle TEXT DEFAULT '',
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            labor_cost REAL DEFAULT 0,
            parts_cost REAL DEFAULT 0,
            total REAL DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(bike_id) REFERENCES bikes(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE repair_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repair_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY(repair_id) REFERENCES repairs(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
    """)
    conn.commit()
    print("  ✅  Schema created")

    # ── Users ────────────────────────────────────────────────
    conn.execute("INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)",
                 ("admin", generate_password_hash("admin123"), "Maouia Gares", "admin"))
    conn.commit()
    print("  👤  Users seeded")

    # ── Suppliers ────────────────────────────────────────────
    for s in SUPPLIERS:
        conn.execute("INSERT INTO suppliers (name,phone,email,address,notes) VALUES (?,?,?,?,?)", s)
    conn.commit()
    sup_ids = [r[0] for r in conn.execute("SELECT id FROM suppliers").fetchall()]
    print(f"  🏭  {len(SUPPLIERS)} suppliers seeded")

    # ── Products ─────────────────────────────────────────────
    for p in PARTS:
        ref, name, cat, brand, buy, sell, minst = p
        qty = random.randint(minst, minst * 8)
        conn.execute("""INSERT INTO products (ref,name,category,brand,qty,buy_price,sell_price,min_stock)
                        VALUES (?,?,?,?,?,?,?,?)""",
                     (ref, name, cat, brand, qty, buy, sell, minst))
    conn.commit()
    prod_map = {r[1]: r[0] for r in conn.execute("SELECT id,ref FROM products").fetchall()}
    prod_ids = list(prod_map.values())
    print(f"  📦  {len(PARTS)} products seeded")

    # ── Customers ────────────────────────────────────────────
    used_cins = set()
    for i in range(60):
        name    = random_name()
        cin     = random_cin(used_cins)
        phone   = random_phone()
        email   = f"{name.split()[0].lower()}{random.randint(10,99)}@gmail.com"
        address = random_address()
        conn.execute("INSERT INTO customers (name,cin,phone,email,address) VALUES (?,?,?,?,?)",
                     (name, cin, phone, email, address))
    conn.commit()
    cust_ids = [r[0] for r in conn.execute("SELECT id FROM customers").fetchall()]
    print(f"  👤  {len(cust_ids)} customers seeded")

    # ── Bikes ────────────────────────────────────────────────
    # Each customer owns 1-2 bikes (a few own none, a few own 2, to mirror real life)
    used_plates = set()
    def random_plate():
        while True:
            n  = random.randint(1, 299)
            n2 = random.randint(1000, 9999)
            plate = f"{n} TUN {n2}"
            if plate not in used_plates:
                used_plates.add(plate)
                return plate

    bike_ids_by_customer = {}
    for cid in cust_ids:
        n_bikes = random.choices([0, 1, 1, 1, 2], weights=[10, 50, 20, 10, 10])[0]
        bike_ids_by_customer[cid] = []
        for _ in range(n_bikes):
            brand = random.choice(MOTO_BRANDS)
            model = random.choice(MOTO_MODELS[brand])
            year  = random.randint(2014, 2025)
            plate = random_plate()
            color = random.choice(["Noir", "Rouge", "Blanc", "Bleu", "Gris", "Vert", "Bordeaux"])
            mileage = random.randint(500, 60000)
            conn.execute("""INSERT INTO bikes (owner_id,brand,model,year,plate,color,mileage)
                            VALUES (?,?,?,?,?,?,?)""",
                         (cid, brand, model, year, plate, color, mileage))
            bid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            bike_ids_by_customer[cid].append(bid)
    conn.commit()
    n_bikes_total = conn.execute("SELECT COUNT(*) FROM bikes").fetchone()[0]
    print(f"  🏍  {n_bikes_total} bikes seeded")

    # ── Purchases (restock history) ──────────────────────────
    print("  🛒  Seeding purchases…")
    for _ in range(120):
        pid    = random.choice(prod_ids)
        sup_id = random.choice(sup_ids)
        qty    = random.randint(5, 50)
        prow   = conn.execute("SELECT buy_price FROM products WHERE id=?", (pid,)).fetchone()
        price  = round(prow[0] * random.uniform(0.85, 1.0), 2)
        dt     = rand_date(500)
        conn.execute("""INSERT INTO purchases (supplier_id,product_id,user_id,qty,unit_price,total,note,created_at)
                        VALUES (?,?,?,?,?,?,?,?)""",
                     (sup_id, pid, 1, qty, price, qty*price, "", dt))
    conn.commit()

    # ── Sales ────────────────────────────────────────────────
    print("  💰  Seeding sales…")
    for _ in range(200):
        cid      = random.choice(cust_ids + [None, None])  # some walk-ins
        dt       = rand_date(365)
        n_items  = random.randint(1, 4)
        items    = []
        subtotal = 0.0

        chosen = random.sample(prod_ids, min(n_items, len(prod_ids)))
        for pid in chosen:
            prow = conn.execute("SELECT sell_price, qty FROM products WHERE id=?", (pid,)).fetchone()
            if prow[1] < 1:
                continue
            qty   = random.randint(1, min(3, prow[1]))
            price = round(prow[0] * random.uniform(0.95, 1.05), 2)
            items.append((pid, qty, price))
            subtotal += qty * price
            conn.execute("UPDATE products SET qty = qty - ? WHERE id=?", (qty, pid))

        if not items:
            continue

        discount = round(random.choice([0, 0, 0, 0, 2, 5, 10, 0]), 2)
        total    = max(subtotal - discount, 0)

        conn.execute("""INSERT INTO sales (customer_id,user_id,total,discount,note,created_at)
                        VALUES (?,?,?,?,?,?)""",
                     (cid, 1, total, discount, "", dt))
        sid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        for pid, qty, price in items:
            conn.execute("INSERT INTO sale_items (sale_id,product_id,qty,unit_price) VALUES (?,?,?,?)",
                         (sid, pid, qty, price))

        if cid:
            conn.execute("UPDATE customers SET ts = ts + ? WHERE id=?", (total, cid))

    conn.commit()
    n_sales = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    print(f"  💰  {n_sales} sales seeded")

    # ── Repairs ──────────────────────────────────────────────
    print("  🔧  Seeding repairs…")
    for _ in range(80):
        cid          = random.choice(cust_ids)
        owned_bikes  = bike_ids_by_customer.get(cid, [])
        bike_id      = random.choice(owned_bikes) if owned_bikes else None
        vehicle      = "" if bike_id else random_vehicle()  # fallback text only if no real bike
        job          = random.choice(REPAIR_JOBS)
        desc, labor, part_refs = job
        status  = random.choice(REPAIR_STATUSES)
        dt      = rand_date(365)
        note    = random.choice(["Client pressé", "Devis accepté", "En attente pièce",
                                  "RDV confirmé", "", "", ""])

        parts_cost = 0.0
        valid_parts = []
        for ref in part_refs:
            pid  = prod_map.get(ref)
            if not pid:
                continue
            prow = conn.execute("SELECT sell_price, qty FROM products WHERE id=?", (pid,)).fetchone()
            if not prow or prow[1] < 1:
                continue
            qty   = 1
            price = prow[0]
            valid_parts.append((pid, qty, price))
            parts_cost += qty * price

        total = labor + parts_cost

        conn.execute("""INSERT INTO repairs
                        (customer_id,bike_id,user_id,vehicle,description,status,labor_cost,parts_cost,total,note,created_at,updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (cid, bike_id, 1, vehicle, desc, status, labor, parts_cost, total, note, dt, dt))
        rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        if status == "done":
            for pid, qty, price in valid_parts:
                conn.execute("INSERT INTO repair_parts (repair_id,product_id,qty,unit_price) VALUES (?,?,?,?)",
                             (rid, pid, qty, price))
                conn.execute("UPDATE products SET qty = qty - ? WHERE id=?", (qty, pid))

    conn.commit()
    n_repairs = conn.execute("SELECT COUNT(*) FROM repairs").fetchone()[0]
    print(f"  🔧  {n_repairs} repairs seeded")

    # ── Summary ──────────────────────────────────────────────
    conn.close()
    total_rev = sum(r[0] for r in sqlite3.connect(DB_FILE).execute("SELECT total FROM sales").fetchall())
    print(f"\n  ✅  Database ready: {DB_FILE}")
    print(f"  📊  Summary:")
    print(f"      Products  : {len(PARTS)}")
    print(f"      Customers : 60")
    print(f"      Suppliers : {len(SUPPLIERS)}")
    print(f"      Sales     : {n_sales}  (revenue ≈ {total_rev:,.0f} TND)")
    print(f"      Repairs   : {n_repairs}")
    print(f"\n  🔑  Login: admin / admin123\n")

if __name__ == "__main__":
    build()
