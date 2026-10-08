# Minimalist Full-Stack Web Hub & Mini-Games

Flask + SQLite + Tailwind (CDN) + Vanilla JS.

## Lokal ishga tushirish

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
ADMIN_PASSWORD=ozparolingiz python app.py
```

- Sayt: http://127.0.0.1:5000
- Admin: http://127.0.0.1:5000/admin (login: `admin`)

## Muhit o'zgaruvchilari

| Nom | Vazifasi |
|---|---|
| `SECRET_KEY` | Sessiya kaliti (productionda majburiy, uzun tasodifiy qator) |
| `ADMIN_USER` | Admin logini (default `admin`) |
| `ADMIN_PASSWORD` | Admin paroli (default `admin123` — albatta o'zgartiring!) |
| `ADMIN_PASSWORD_HASH` | Ixtiyoriy: tayyor hash (`werkzeug.security.generate_password_hash`) |
| `ADMIN_PATH` | Maxfiy URL (default `admin`, masalan `my-secret-door`) |
| `DATA_DIR` | SQLite va rasmlar papkasi (Renderda `/var/data`) |

## Render'ga deploy

1. Kodni GitHub'ga yuklang.
2. Render → New → Blueprint → repozitoriyni tanlang (`render.yaml` avtomatik o'qiladi).
3. `ADMIN_PASSWORD` ni dashboardda kiriting, `ADMIN_PATH` ni o'zgartiring.

**Muhim:** Renderning bepul rejasida fayl tizimi vaqtinchalik — har deployda SQLite va yuklangan rasmlar yo'qoladi.
Ma'lumot saqlanishi uchun pullik reja + Persistent Disk (`render.yaml`da sozlangan) yoki tashqi baza (masalan, Postgres) kerak.
