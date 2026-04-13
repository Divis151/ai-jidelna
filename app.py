from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import os
import time
import datetime
import requests

# =========================
# ZÁKLADNÍ NASTAVENÍ APLIKACE
# =========================

# Vytvoření Flask aplikace
app = Flask(__name__)

# Secret key je potřeba pro Flask session (přihlášení uživatele)
# Pro školní projekt stačí natvrdo, v reálné aplikaci by měl být mimo kód.
app.secret_key = "tajny_klic_pro_skolarni_demo"

# Připojení do PostgreSQL databáze
# Hodnota se bere z proměnné prostředí, výchozí odpovídá Docker Compose.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://student:heslo123@db:5432/myapp"
)

# Přístup k externímu AI API
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

# SQLAlchemy engine – objekt pro komunikaci s databází
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Testovací účty
# Přihlášení je řešeno jednoduše, uživatelé jsou natvrdo v kódu.
USERS = {
    "student1": "heslo123",
    "student2": "heslo123",
    "student3": "heslo123",
}


# =========================
# ČEKÁNÍ NA DATABÁZI
# =========================

# Docker Compose spouští app i db současně,
# proto může databáze startovat pomaleji než aplikace.
for i in range(20):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        break
    except OperationalError:
        time.sleep(2)


# =========================
# VYTVOŘENÍ / OPRAVA TABULKY
# =========================

# Pokud tabulka ještě neexistuje, aplikace ji vytvoří.
# Pokud existuje starší verze tabulky bez sloupce username,
# pokusí se ho doplnit pomocí ALTER TABLE.
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS prompts (
            id SERIAL PRIMARY KEY,
            username TEXT,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # Oprava starší databáze – pokud sloupec username ještě neexistuje,
    # pokusí se ho přidat. Pokud už existuje, chyba se ignoruje.
    try:
        conn.execute(text("ALTER TABLE prompts ADD COLUMN username TEXT;"))
    except Exception:
        pass

    conn.commit()


# =========================
# HTML ŠABLONY
# =========================

LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Přihlášení</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #eef2f7, #dfe8f3);
            margin: 0;
            padding: 40px;
            color: #1f2937;
        }
        .card {
            max-width: 420px;
            margin: 60px auto;
            background: white;
            border-radius: 18px;
            padding: 28px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        }
        h1 {
            margin-top: 0;
        }
        input {
            width: 100%;
            padding: 12px;
            margin-top: 10px;
            margin-bottom: 14px;
            border: 1px solid #d1d9e0;
            border-radius: 10px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 10px;
            background: #2563eb;
            color: white;
            cursor: pointer;
            font-size: 15px;
        }
        button:hover {
            background: #1d4ed8;
        }
        .error {
            margin-top: 12px;
            color: #b91c1c;
            font-size: 14px;
        }
        .hint {
            margin-top: 16px;
            font-size: 13px;
            color: #6b7280;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>🔐 Přihlášení</h1>
        <p>Přihlas se do aplikace AI školní jídelna.</p>

        <form method="post" action="/login">
            <input type="text" name="username" placeholder="Uživatelské jméno" required>
            <input type="password" name="password" placeholder="Heslo" required>
            <button type="submit">Přihlásit</button>
        </form>

        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}

        <div class="hint">
            Testovací účty: student1, student2, student3<br>
            Heslo: heslo123
        </div>
    </div>
</body>
</html>
"""

HTML_PAGE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>AI školní jídelna</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #eef2f7, #dfe8f3);
            margin: 0;
            padding: 32px;
            color: #1f2937;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
        }

        .hero {
            background: white;
            border-radius: 18px;
            padding: 28px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            margin-bottom: 24px;
        }

        .hero h1 {
            margin: 0 0 10px 0;
            font-size: 32px;
        }

        .hero p {
            margin: 0;
            color: #5b6470;
        }

        .author {
            margin-top: 12px;
            font-size: 14px;
            color: #374151;
            font-weight: bold;
        }

        .userbox {
            margin-top: 14px;
            font-size: 14px;
            color: #111827;
        }

        .logout-link {
            margin-left: 12px;
            color: #b91c1c;
            text-decoration: none;
            font-weight: bold;
        }

        .logout-link:hover {
            text-decoration: underline;
        }

        .grid {
            display: grid;
            grid-template-columns: 1.1fr 0.9fr;
            gap: 24px;
        }

        .card {
            background: white;
            border-radius: 18px;
            padding: 22px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        }

        .card h2 {
            margin-top: 0;
        }

        .row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        input[type="text"] {
            flex: 1;
            min-width: 260px;
            padding: 14px;
            border: 1px solid #d1d9e0;
            border-radius: 10px;
            font-size: 15px;
            box-sizing: border-box;
        }

        button {
            padding: 12px 16px;
            border: none;
            border-radius: 10px;
            background: #2563eb;
            color: white;
            font-size: 15px;
            cursor: pointer;
        }

        button:hover {
            background: #1d4ed8;
        }

        .mini-buttons form {
            display: inline-block;
            margin-right: 8px;
            margin-bottom: 8px;
        }

        .answer {
            margin-top: 18px;
            background: #eff6ff;
            border-left: 5px solid #2563eb;
            padding: 14px;
            border-radius: 10px;
            white-space: pre-wrap;
        }

        .muted {
            color: #6b7280;
            font-size: 14px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        th, td {
            padding: 10px 8px;
            border-bottom: 1px solid #edf2f7;
            text-align: left;
            vertical-align: top;
        }

        th {
            background: #f8fafc;
        }

        .badge {
            display: inline-block;
            background: #e0f2fe;
            color: #075985;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            margin-right: 8px;
        }

        @media (max-width: 860px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="hero">
        <h1>🍽️ AI školní jídelna</h1>
        <p>Flask + PostgreSQL + vzdálené AI API. Dotaz se odešle AI a uloží do databáze.</p>
        <div class="author">Autor: Ondrej Divis 13/04/2026</div>
        <div class="userbox">
            Přihlášený uživatel: <b>{{ username }}</b>
            <a class="logout-link" href="/logout">Odhlásit</a>
        </div>
        <div style="margin-top: 12px;">
            <span class="badge">Docker Compose</span>
            <span class="badge">PostgreSQL</span>
            <span class="badge">AI API</span>
            <span class="badge">Přihlášení uživatele</span>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Zeptat se AI</h2>
            <p class="muted">Zadej dotaz a aplikace ho pošle AI. Odpověď se zároveň uloží do databáze.</p>

            <div class="mini-buttons">
                <form action="/ping" method="get">
                    <button type="submit">Ping</button>
                </form>
                <form action="/status" method="get">
                    <button type="submit">Status</button>
                </form>
            </div>

            <hr>

            <form method="post" action="/ask">
                <div class="row">
                    <input type="text" name="prompt" placeholder="Např. Co si mám dát dnes ve školní jídelně?" required>
                    <button type="submit">Odeslat dotaz</button>
                </div>
            </form>

            {% if answer %}
            <h3>Odpověď AI</h3>
            <div class="answer">{{ answer }}</div>
            {% endif %}
        </div>

        <div class="card">
            <h2>Info o aplikaci</h2>
            <p class="muted">
                Aplikace běží ve Flasku v Dockeru. Databáze je PostgreSQL ve druhé službě
                a AI odpovědi chodí z OpenAI-compatible API.
            </p>
            <ul>
                <li><b>/</b> – GUI</li>
                <li><b>/login</b> – přihlášení</li>
                <li><b>/logout</b> – odhlášení</li>
                <li><b>/ping</b> – test dostupnosti</li>
                <li><b>/status</b> – JSON o stavu</li>
                <li><b>/ai</b> – API endpoint pro POST dotaz</li>
            </ul>
        </div>
    </div>

    <div class="card" style="margin-top: 24px;">
        <h2>Moje historie dotazů</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Dotaz</th>
                    <th>Odpověď</th>
                    <th>Čas</th>
                </tr>
            </thead>
            <tbody>
                {% for item in history %}
                <tr>
                    <td>{{ item.id }}</td>
                    <td>{{ item.prompt }}</td>
                    <td>{{ item.response }}</td>
                    <td>{{ item.created_at }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
</body>
</html>
"""


# =========================
# POMOCNÉ FUNKCE
# =========================

def is_logged_in():
    """
    Vrací True, pokud je uživatel přihlášen.
    """
    return "username" in session


def call_ai(user_input: str) -> str:
    """
    Zavolá vzdálené OpenAI-compatible API a vrátí text odpovědi.
    """
    if not OPENAI_API_KEY:
        return "Chyba konfigurace: chybí OPENAI_API_KEY."

    prompt = (
        "Jsi stručný poradce školní jídelny. "
        "Odpovídej česky, maximálně dvěma větami, prakticky a bez omáčky.\n\n"
        f"Dotaz uživatele: {user_input}"
    )

    try:
        response = requests.post(
            f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gemma3:27b",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
            },
            timeout=90,
            verify=False
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        return f"AI chyba: {str(e)}"


def get_history(username: str):
    """
    Načte posledních 20 dotazů pouze pro konkrétního uživatele.
    Tím zajistíme, že student uvidí jen svou vlastní historii.
    """
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, prompt, response, created_at
            FROM prompts
            WHERE username = :username
            ORDER BY id DESC
            LIMIT 20
        """), {"username": username}).fetchall()

    return [
        {
            "id": row[0],
            "prompt": row[1],
            "response": row[2],
            "created_at": row[3],
        }
        for row in rows
    ]


def save_prompt(username: str, prompt_text: str, response_text: str):
    """
    Uloží dotaz a odpověď do databáze spolu se jménem uživatele.
    """
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO prompts (username, prompt, response)
                VALUES (:username, :prompt, :response)
            """),
            {
                "username": username,
                "prompt": prompt_text,
                "response": response_text,
            },
        )
        conn.commit()


# =========================
# ROUTY – PŘIHLÁŠENÍ
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Přihlašovací stránka:
    - GET zobrazí formulář
    - POST ověří jméno a heslo
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username in USERS and USERS[username] == password:
            session["username"] = username
            return redirect(url_for("index"))

        return render_template_string(LOGIN_PAGE, error="Neplatné přihlašovací údaje.")

    return render_template_string(LOGIN_PAGE, error=None)


@app.route("/logout")
def logout():
    """
    Odhlášení uživatele – smaže session.
    """
    session.pop("username", None)
    return redirect(url_for("login"))


# =========================
# ROUTY – HLAVNÍ ČÁST APPKY
# =========================

@app.route("/", methods=["GET"])
def index():
    """
    Hlavní stránka aplikace.
    Pokud není uživatel přihlášený, přesměruje ho na login.
    """
    if not is_logged_in():
        return redirect(url_for("login"))

    return render_template_string(
        HTML_PAGE,
        answer=None,
        history=get_history(session["username"]),
        username=session["username"]
    )


@app.route("/ask", methods=["POST"])
def ask():
    """
    Zpracuje formulář z GUI:
    - ověří přihlášení
    - vezme dotaz
    - pošle ho AI
    - uloží do DB
    - vrátí stránku s odpovědí
    """
    if not is_logged_in():
        return redirect(url_for("login"))

    user_input = request.form.get("prompt", "").strip()
    answer = call_ai(user_input)
    save_prompt(session["username"], user_input, answer)

    return render_template_string(
        HTML_PAGE,
        answer=answer,
        history=get_history(session["username"]),
        username=session["username"]
    )


@app.route("/ping", methods=["GET"])
def ping():
    """
    Jednoduchý test endpoint.
    """
    return "pong"


@app.route("/status", methods=["GET"])
def status():
    """
    Vrací JSON se stavem aplikace.
    """
    return jsonify({
        "time": str(datetime.datetime.now()),
        "author": "Ondřej Diviš",
        "database": "ok",
        "ai_base_url": OPENAI_BASE_URL,
        "app": "running",
        "logged_in_user": session.get("username", None)
    })


@app.route("/ai", methods=["POST"])
def ai():
    """
    API endpoint pro AI dotaz přes JSON.
    Vyžaduje přihlášení uživatele.
    """
    if not is_logged_in():
        return jsonify({"error": "Nejste přihlášen."}), 401

    data = request.get_json(silent=True) or {}
    user_input = data.get("prompt", "").strip()

    answer = call_ai(user_input)
    save_prompt(session["username"], user_input, answer)

    return jsonify({
        "username": session["username"],
        "prompt": user_input,
        "response": answer
    })


# =========================
# START APLIKACE
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
