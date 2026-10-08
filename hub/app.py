import os
import sqlite3
import secrets
import time
import uuid
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "hub.db")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ADMIN_PATH = os.environ.get("ADMIN_PATH", "admin").strip("/")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
_pw_hash = os.environ.get("ADMIN_PASSWORD_HASH")
if not _pw_hash:
    # Lokal ishlab chiqish uchun. Productionda ADMIN_PASSWORD yoki ADMIN_PASSWORD_HASH majburiy.
    _pw_hash = generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123"))
ADMIN_PASSWORD_HASH = _pw_hash

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    MAX_CONTENT_LENGTH=6 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
)


# ---------- DB ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            image TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS comments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
            author TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS likes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
            visitor TEXT NOT NULL,
            UNIQUE(post_id, visitor)
        );
        """
    )
    db.commit()
    db.close()


init_db()


def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


@app.template_filter("date")
def fmt_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y")
    except Exception:
        return s


# ---------- Visitor cookie (parolsiz, layk takrorlanmasligi uchun) ----------
@app.before_request
def ensure_visitor():
    if "vid" not in session:
        session["vid"] = secrets.token_hex(16)
        session.permanent = True


# ---------- Admin yordamchilari ----------
def admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*a, **kw)
    return wrapper


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


def check_csrf():
    sent = request.form.get("csrf") or request.headers.get("X-CSRF", "")
    if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
        abort(400)


_attempts = {}


def too_many_attempts(ip):
    t = time.time()
    _attempts[ip] = [x for x in _attempts.get(ip, []) if t - x < 600]
    return len(_attempts[ip]) >= 5


# ---------- Ommaviy sahifalar ----------
@app.route("/")
def index():
    db = get_db()
    vid = session["vid"]
    posts = db.execute(
        """SELECT p.*,
                  (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count,
                  EXISTS(SELECT 1 FROM likes l WHERE l.post_id = p.id AND l.visitor = ?) AS liked
           FROM posts p ORDER BY p.id DESC""",
        (vid,),
    ).fetchall()
    comments = {}
    for c in db.execute("SELECT * FROM comments ORDER BY id ASC").fetchall():
        comments.setdefault(c["post_id"], []).append(c)
    return render_template("index.html", posts=posts, comments=comments)


@app.route("/games")
def games():
    return render_template("games.html")


@app.route("/uploads/<path:name>")
def uploads(name):
    return send_from_directory(UPLOAD_DIR, name)


@app.post("/api/posts/<int:post_id>/like")
def api_like(post_id):
    db = get_db()
    if not db.execute("SELECT 1 FROM posts WHERE id=?", (post_id,)).fetchone():
        abort(404)
    vid = session["vid"]
    cur = db.execute("DELETE FROM likes WHERE post_id=? AND visitor=?", (post_id, vid))
    liked = False
    if cur.rowcount == 0:
        db.execute("INSERT INTO likes(post_id, visitor) VALUES(?,?)", (post_id, vid))
        liked = True
    db.commit()
    count = db.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,)).fetchone()[0]
    return jsonify(liked=liked, count=count)


@app.post("/api/posts/<int:post_id>/comments")
def api_comment(post_id):
    db = get_db()
    if not db.execute("SELECT 1 FROM posts WHERE id=?", (post_id,)).fetchone():
        abort(404)
    data = request.get_json(silent=True) or {}
    author = (data.get("author") or "").strip()[:40] or "Mehmon"
    body = (data.get("body") or "").strip()[:1000]
    if not body:
        return jsonify(error="Izoh bo'sh bo'lishi mumkin emas"), 400
    ts = now()
    db.execute(
        "INSERT INTO comments(post_id, author, body, created_at) VALUES(?,?,?,?)",
        (post_id, author, body, ts),
    )
    db.commit()
    return jsonify(author=author, body=body, date=fmt_date(ts)), 201


# ---------- Admin ----------
@app.route(f"/{ADMIN_PATH}", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_panel"))
    error = None
    if request.method == "POST":
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
        if too_many_attempts(ip):
            error = "Juda ko'p urinish. 10 daqiqadan keyin qayta urinib ko'ring."
        else:
            user = request.form.get("username", "")
            pw = request.form.get("password", "")
            ok = secrets.compare_digest(user, ADMIN_USER) and check_password_hash(ADMIN_PASSWORD_HASH, pw)
            if ok:
                session.clear()
                session["is_admin"] = True
                session["vid"] = secrets.token_hex(16)
                return redirect(url_for("admin_panel"))
            _attempts.setdefault(ip, []).append(time.time())
            error = "Login yoki parol noto'g'ri."
    return render_template("admin_login.html", error=error)


@app.route(f"/{ADMIN_PATH}/panel")
@admin_required
def admin_panel():
    posts = get_db().execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    return render_template("admin.html", posts=posts)


@app.post(f"/{ADMIN_PATH}/posts")
@admin_required
def admin_create_post():
    check_csrf()
    title = request.form.get("title", "").strip()[:200]
    body = request.form.get("body", "").strip()[:20000]
    if not title or not body:
        flash("Sarlavha va matn majburiy.")
        return redirect(url_for("admin_panel"))
    image_name = None
    f = request.files.get("image")
    if f and f.filename:
        ext = secure_filename(f.filename).rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXT:
            flash("Faqat png, jpg, gif, webp rasmlar ruxsat etiladi.")
            return redirect(url_for("admin_panel"))
        image_name = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(UPLOAD_DIR, image_name))
    db = get_db()
    db.execute(
        "INSERT INTO posts(title, body, image, created_at) VALUES(?,?,?,?)",
        (title, body, image_name, now()),
    )
    db.commit()
    flash("Post qo'shildi.")
    return redirect(url_for("admin_panel"))


@app.post(f"/{ADMIN_PATH}/posts/<int:post_id>/delete")
@admin_required
def admin_delete_post(post_id):
    check_csrf()
    db = get_db()
    row = db.execute("SELECT image FROM posts WHERE id=?", (post_id,)).fetchone()
    if row:
        if row["image"]:
            try:
                os.remove(os.path.join(UPLOAD_DIR, row["image"]))
            except OSError:
                pass
        db.execute("DELETE FROM posts WHERE id=?", (post_id,))
        db.commit()
        flash("Post o'chirildi.")
    return redirect(url_for("admin_panel"))


@app.post(f"/{ADMIN_PATH}/comments/<int:cid>/delete")
@admin_required
def admin_delete_comment(cid):
    check_csrf()
    db = get_db()
    db.execute("DELETE FROM comments WHERE id=?", (cid,))
    db.commit()
    return redirect(request.referrer or url_for("index"))


@app.post(f"/{ADMIN_PATH}/logout")
@admin_required
def admin_logout():
    check_csrf()
    session.clear()
    return redirect(url_for("index"))


@app.errorhandler(413)
def too_large(_):
    flash("Fayl juda katta (maks. 6 MB).")
    return redirect(url_for("admin_panel") if session.get("is_admin") else url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
