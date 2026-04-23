from flask import Flask, jsonify, request, render_template_string, session, redirect
import sqlite3
import requests
import difflib
import smtplib

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("db.sqlite")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- DATA ----------------
data = {"news": []}

# ---------------- FAKE SCORE ----------------
def fake_score(text):
    score = 0
    text = text.lower()

    keywords = ["şok", "son dakika", "inanılmaz", "öldü", "ifşa", "gizli"]

    for k in keywords:
        if k in text:
            score += 15

    if text.isupper():
        score += 20

    if len(text) < 20:
        score += 10

    return min(score, 100)

# ---------------- SIMILARITY ----------------
def similarity(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

# ---------------- AUTH ----------------
@app.route("/register", methods=["POST"])
def register():
    u = request.json["username"]
    p = request.json["password"]

    conn = sqlite3.connect("db.sqlite")
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?,?)", (u, p))
    conn.commit()
    conn.close()

    return {"ok": True}

@app.route("/login", methods=["POST"])
def login():
    u = request.json["username"]
    p = request.json["password"]

    conn = sqlite3.connect("db.sqlite")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
    user = c.fetchone()
    conn.close()

    if user:
        session["user"] = u
        return {"ok": True}

    return {"ok": False}

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- EMAIL ----------------
def send_email(rumeyysauslu@gmail.com):
    try:
        sender = "tubitaktest0@gmail.com"   # BURAYA kendi mailini yaz
        password = "umdyxtmpeljhodhy"          # Gmail App Password

        message = "Subject: Risk Uyarısı\n\nYüksek riskli haber tespit edildi!"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, to, message)
        server.quit()
    except Exception as e:
        print("Mail hata:", e)

# ---------------- ANALYZE ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text", "")
    score = fake_score(text)

    similar_news = []
    for n in data["news"]:
        if similarity(text, n["text"]) > 0.6:
            similar_news.append(n)

    result = {
        "text": text,
        "risk": score,
        "similar": similar_news
    }

    data["news"].append(result)

    # 🚨 yüksek riskte mail
    if score > 70:

    return result

# ---------------- NEWS ----------------
@app.route("/api/news")
def get_news():
    url = "https://newsapi.org/v2/top-headlines?country=tr&apiKey=YOUR_API_KEY"

    try:
        res = requests.get(url).json()
        articles = res.get("articles", [])[:5]

        result = []
        for a in articles:
            title = a.get("title", "")
            result.append({
                "title": title,
                "risk": fake_score(title)
            })

        return {"news": result}
    except:
        return {"news": []}

# ---------------- TRENDS ----------------
@app.route("/api/trends")
def trends():
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR"

    try:
        res = requests.get(url).text
        items = res.split("<title>")[1:6]

        data_list = []
        for i in items:
            data_list.append(i.split("</title>")[0])

        return {"trends": data_list}
    except:
        return {"trends": []}

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    return render_template_string("""
    <h1>Risk Panel</h1>

    <input id="text">
    <button onclick="send()">Analiz</button>

    <p id="res"></p>

    <h2>Haberler</h2>
    <div id="news"></div>

    <h2>Trendler</h2>
    <div id="trends"></div>

    <script>
    async function send(){
        let t = document.getElementById("text").value;

        let r = await fetch("/api/analyze",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify({text:t})
        });

        let j = await r.json();
        document.getElementById("res").innerText = "Risk: " + j.risk;
    }

    async function loadNews(){
        let r = await fetch("/api/news");
        let j = await r.json();

        let html="";
        j.news.forEach(n=>{
            html += "<p>"+n.title+" ("+n.risk+")</p>";
        });

        document.getElementById("news").innerHTML = html;
    }

    async function loadTrends(){
        let r = await fetch("/api/trends");
        let j = await r.json();

        let html="";
        j.trends.forEach(t=>{
            html += "<p>"+t+"</p>";
        });

        document.getElementById("trends").innerHTML = html;
    }

    setInterval(loadNews,5000);
    setInterval(loadTrends,7000);
    </script>
    """)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return {"ok": True}

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()