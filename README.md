# 🍽️ AI školní jídelna

Tento projekt představuje webovou aplikaci vytvořenou v Pythonu (Flask), která umožňuje studentům komunikovat s umělou inteligencí a získat doporučení na jídlo ve školní jídelně.

Aplikace využívá moderní architekturu založenou na Docker Compose, kde jsou odděleny jednotlivé služby (webová aplikace a databáze).

---

# 🎯 Cíl projektu

Cílem projektu bylo:

- vytvořit webovou aplikaci komunikující s AI
- naučit se pracovat s Docker Compose (více kontejnerů)
- implementovat databázi (PostgreSQL)
- zajistit ukládání dat (historie dotazů)
- vytvořit jednoduché přihlášení uživatelů
- propojit backend s externím API

---

# 🧱 Architektura aplikace

Aplikace je rozdělena na dvě hlavní části:

## 1️⃣ Webová aplikace (Flask)

- běží na portu 5000
- zpracovává HTTP požadavky
- komunikuje s AI API
- ukládá data do databáze

## 2️⃣ Databáze (PostgreSQL)

- ukládá historii dotazů
- běží v samostatném Docker kontejneru
- data jsou perzistentní (uložená v `/data`)

---

## 📊 Schéma komunikace


Uživatel → Flask aplikace → AI API
↓
PostgreSQL databáze


---

# 🚀 Funkce aplikace

- Přihlášení uživatele
- Odeslání dotazu na AI
- Zobrazení odpovědi
- Uložení dotazu i odpovědi do databáze
- Zobrazení historie dotazů
- Oddělení historie podle uživatele
- REST API endpoint (`/ai`)

---

# 🔐 Přihlášení uživatelů

Přihlášení je řešeno jednoduše pomocí pevně definovaných uživatelů v kódu.

| Uživatel | Heslo |
|--------|------|
| student1 | heslo123 |
| student2 | heslo123 |
| student3 | heslo123 |

👉 Hesla nejsou ukládána v databázi – jedná se o demonstrační řešení.

---

# 🗄️ Databáze

Použita databáze PostgreSQL.

## Tabulka `prompts`

| Sloupec | Popis |
|--------|------|
| id | primární klíč |
| username | uživatel |
| prompt | dotaz |
| response | odpověď |
| created_at | čas vytvoření |

---

# 🤖 AI integrace

Aplikace komunikuje s externím AI API kompatibilním s OpenAI.

## Použité API:


https://kurim.ithope.eu/v1


## Model:


gemma3:27b


---

# ⚙️ Proměnné prostředí

Před spuštěním je nutné nastavit:

```bash
export OPENAI_API_KEY="TVUJ_API_KLIC"
export OPENAI_BASE_URL="https://kurim.ithope.eu/v1"
🐳 Docker Compose

Projekt využívá compose.yml obsahující dvě služby:

app
build z Dockerfile
běží Flask aplikace
db
image: postgres:16-alpine
obsahuje databázi
▶️ Spuštění aplikace
1. Stažení projektu
git clone https://github.com/TVUJ_USERNAME/ai-jidelna.git
cd ai-jidelna
2. Nastavení proměnných
export OPENAI_API_KEY="TVUJ_API_KLIC"
export OPENAI_BASE_URL="https://kurim.ithope.eu/v1"
3. Spuštění
docker compose up --build
4. Otevření aplikace
http://localhost:5000
🔄 Jak aplikace funguje (detailně)
Uživatel se přihlásí
Flask uloží uživatele do session
Uživatel zadá dotaz
Aplikace odešle dotaz na AI API
AI vrátí odpověď
Aplikace uloží dotaz i odpověď do databáze
Historie se zobrazí pouze přihlášenému uživateli
🌐 API endpointy
Endpoint	Metoda	Popis
/	GET	GUI
/login	GET/POST	přihlášení
/logout	GET	odhlášení
/ask	POST	formulář
/ai	POST	API dotaz
/ping	GET	test
/status	GET	stav
🔒 Bezpečnost
API klíč není uložen v kódu
používají se environment variables
session spravuje Flask
každý uživatel vidí pouze své dotazy
⚠️ Omezení
uživatelé jsou hardcoded
hesla nejsou hashovaná
aplikace není určena pro produkční nasazení
🚀 Možná rozšíření
registrace uživatelů
ukládání uživatelů do databáze
hashování hesel
moderní frontend (React)
lepší UI/UX
cache (Redis)
👨‍💻 Autor

Ondřej Diviš

📚 Použité technologie
Python
Flask
PostgreSQL
SQLAlchemy
Docker
Docker Compose
OpenAI API
