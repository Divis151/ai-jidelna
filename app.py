from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import os
import time
import datetime
import requests

app = Flask(__name__)

app.secret_key = "tajny_klic_pro_skolarni_demo"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://student:heslo123@db:5432/myapp"
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

USERS = {
    "student1": "heslo123",
    "student2": "heslo123",
    "student3": "heslo123",
}

for i in range(20):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        break
    except OperationalError:
        time.sleep(2)

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

    try:
        conn.execute(text("ALTER TABLE prompts ADD COLUMN username TEXT;"))
    except Exception:
        pass

    conn.commit()

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

HTML_PAGE = """... (zbytek HTML zůstává úplně stejný, jen bez komentářů — nic jsem v něm neměnil)"""

def is_logged_in():
    return "username" in session

def call_ai(user_input: str) -> str:
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

@app.route("/login", methods=["GET", "POST"])
def login():
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
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET"])
def index():
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
    return "pong"

@app.route("/status", methods=["GET"])
def status():
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
