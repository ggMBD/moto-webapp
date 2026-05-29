# 🏍 MotoShop Manager

A full web app for managing your moto parts shop.
Built with **Python Flask** (backend) + **HTML/CSS/JS** (frontend) + **SQLite** (database).

---

## ⚡ Quick Start

### 1. Install Flask
```bash
pip install flask
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

That's it! The database file `motoshop.db` is created automatically.

---

## 📁 Project Structure
```
motoshop/
├── app.py              ← Flask backend + all API routes
├── requirements.txt    ← Python dependencies
├── motoshop.db         ← SQLite database (auto-created)
└── templates/
    └── index.html      ← Full frontend (single page app)
```

---

## ✨ Features
| Module | What it does |
|---|---|
| 🏠 Dashboard | Live stats + low stock alerts + recent sales |
| 📦 Inventory | Add/Edit/Delete parts, search, stock status |
| 💰 Sales | Cart builder, customer select, discount, auto stock deduction |
| 🛒 Purchases | Restock from supplier, auto stock increment |
| 👤 Customers | Full CRUD |
| 🏭 Suppliers | Full CRUD |
| 📊 Reports | Revenue, top products, monthly sales, stock value |

---

## 🔧 Upgrade Ideas
- Add user login (Flask-Login)
- Export to PDF invoices (reportlab or weasyprint)
- Add barcode scanning
- Deploy on a local network so multiple PCs can use it
