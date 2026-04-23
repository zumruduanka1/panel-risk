from flask import Flask, jsonify, request, render_template_string
import requests
import sqlite3
import smtplib

app = Flask(__name__)

# -----------------------------
# VERİ
# -----------------------------
data = {
    "news": []
}

# -----------------------------
# DATABASE
# -----------------------------
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

# -----------------------------
# FAKE NEWS SCORE
# -----------------------------
def fake_score(text):
    score = 0
    text = text.lower()

    keywords = ["şok", "son dakika", "inanılmaz", "öldü", "gizli", "ifşa"]

    for k in keywords:
        if k in text:
            score += 15

    if text.isupper():
        score += 20

    if len(text) < 20:
        score += 10

    return min(score, 100)

# -----------------------------
# ANA
# -----------------------------
@app.route("/")
def home():
    return {"ok": True}

# -----------------------------
# ANALİZ
# -----------------------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text", "")

    score = fake_score(text)

    if score > 60:
        status = "danger"
    elif score > 30:
        status = "suspicious"
    else:
        status = "normal"

    result = {
        "text": text,
        "risk": score,
        "status": status
    }

    data["news"].append(result)
    return result

# -----------------------------
# HABER ÇEKME
# -----------------------------
@app.route("/api/news")
def get_news():
    url = "https://newsapi.org/v2/top-headlines?country=us&apiKey=YOUR_API_KEY"

    try:
        res = requests.get(url).json()
        articles = res.get("articles", [])[:5]

        results = []
        for a in articles:
            title = a.get("title", "")
            score = fake_score(title)

            results.append({
                "title": title,
                "risk": score
            })

        return {"news": results}
    except:
        return {"news": []}

# -----------------------------
# KULLANICI KAYIT
# -----------------------------
@app.route("/api/register", methods=["POST"])
def register():
    u = request.json.get("username")
    p = request.json.get("password")

    conn = sqlite3.connect("db.sqlite")
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?,?)", (u, p))
    conn.commit()
    conn.close()

    return {"ok": True}

# -----------------------------
# EMAIL (opsiyonel)
# -----------------------------
@app.route("/api/email", methods=["POST"])
def send_email():
    try:
        sender = "tubitaktest0@gmail.com"
        password = "umdyxtmpeljhodhy"
        receiver = request.json.get("rumeyysauslu@gmail.com")

        message = "Subject: Risk Alert\n\nRisk seviyesi yükseldi!"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, message)
        server.quit()

        return {"sent": True}
    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# PANEL (UI)
# -----------------------------
@app.route("/panel")
def panel():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Risk Panel</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>

    <h1>Risk Panel</h1>

    <input id="newsInput" placeholder="Haber gir">
    <button onclick="analyze()">Analiz Et</button>

    <p id="result"></p>

    <canvas id="chart"></canvas>

    <h2>Canlı Haberler</h2>
    <div id="news"></div>

    <script>
    let chart;

    async function analyze() {
        const text = document.getElementById('newsInput').value;

        const res = await fetch('/api/analyze', {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({text})
        });

        const json = await res.json();
        document.getElementById('result').innerHTML =
            "Risk: " + json.risk + " (" + json.status + ")";

        loadData();
    }

    async function loadData() {
        const res = await fetch('/api/data');
        const json = await res.json();

        if (!chart) {
            chart = new Chart(document.getElementById('chart'), {
                type: 'line',
                data: {
                    labels: json.news.map((_, i) => i+1),
                    datasets: [{
                        label: 'Risk',
                        data: json.news.map(n => n.risk)
                    }]
                }
            });
        } else {
            chart.data.labels = json.news.map((_, i) => i+1);
            chart.data.datasets[0].data = json.news.map(n => n.risk);
            chart.update();
        }
    }

    async function loadNews() {
        const res = await fetch('/api/news');
        const json = await res.json();

        let html = "";
        json.news.forEach(n => {
            html += `<p>${n.title} → Risk: ${n.risk}</p>`;
        });

        document.getElementById('news').innerHTML = html;
    }

    setInterval(loadData, 3000);
    setInterval(loadNews, 5000);
    </script>

    </body>
    </html>
    """)

# -----------------------------
# DATA API
# -----------------------------
@app.route("/api/data")
def get_data():
    return jsonify(data)

# -----------------------------
if __name__ == "__main__":
    app.run()