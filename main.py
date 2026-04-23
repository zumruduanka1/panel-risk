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
data = {
    "news": []
}

# ---------------- FAKE SCORE (TR) ----------------
def fake_score(text):
    score = 0
    text = text.lower()

    keywords = [
        "şok", "son dakika", "inanılmaz", "öldü",
        "ifşa", "gizli", "gizemli", "şok edici"
    ]

    for k in keywords:
        if k in text:
            score += 15

    if text.isupper():
        score += 20

    if len(text) < 20:
        score += 10

    return min(score, 100)

# ---------------- BENZERLİK ----------------
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

    # 🚨 Risk yüksekse mail gönder
    if score > 70:
        send_email("ALICI_MAIL")

    return result

# ---------------- TÜRKÇE HABER ----------------
@app.route("/api/news")
def get_news():
    url = "https://newsapi.org/v2/top-headlines?country=tr&apiKey=YOUR_API_KEY"

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

# ---------------- SOSYAL MEDYA (YASAL) ----------------
@app.route("/api/social")
def social():
    # Google Trends (yasal veri)
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR"

    try:
        res = requests.get(url).text
        items = res.split("<title>")[1:6]

        trends = []
        for i in items:
            trends.append(i.split("</title>")[0])

        return {"trends": trends}
    except:
        return {"trends": []}

# ---------------- EMAIL ----------------
def send_email(to):
    try:
        sender = "MAILIN"
        password = "APP_PASSWORD"

        message = "Subject: Risk Uyarısı\n\nYüksek riskli haber tespit edildi!"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, to, message)
        server.quit()
    except:
        pass

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    return render_template_string("""
    <html>
    <head>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>

    <body>
    <h1>Türkçe Risk Panel</h1>

    <input id="newsInput" placeholder="Haber gir">
    <button onclick="analyze()">Analiz</button>

    <p id="result"></p>
    <div id="similar"></div>

    <canvas id="chart"></canvas>

    <h2>Türkçe Haberler</h2>
    <div id="news"></div>

    <h2>Trendler</h2>
    <div id="trends"></div>

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
            "Risk: " + json.risk;

        let sim = "<h3>Benzer:</h3>";
        json.similar.forEach(s => {
            sim += "<p>" + s.text + "</p>";
        });

        document.getElementById('similar').innerHTML = sim;

        loadData();
    }

    async function loadData() {
        const res = await fetch('/api/data');
        const json = await res.json();

        if (!chart) {
            chart = new Chart(document.getElementById('chart'), {
                type: 'line',
                data: {
                    labels: json.news.map((_, i)=>i+1),
                    datasets: [{
                        label: 'Risk',
                        data: json.news.map(n=>n.risk)
                    }]
                }
            });
        } else {
            chart.data.labels = json.news.map((_, i)=>i+1);
            chart.data.datasets[0].data = json.news.map(n=>n.risk);
            chart.update();
        }
    }

    async function loadNews() {
        const res = await fetch('/api/news');
        const json = await res.json();

        let html = "";
        json.news.forEach(n=>{
            html += `<p>${n.title} → ${n.risk}</p>`;
        });

        document.getElementById('news').innerHTML = html;
    }

    async function loadTrends() {
        const res = await fetch('/api/social');
        const json = await res.json();

        let html = "";
        json.trends.forEach(t=>{
            html += "<p>"+t+"</p>";
        });

        document.getElementById('trends').innerHTML = html;
    }

    setInterval(loadData, 3000);
    setInterval(loadNews, 5000);
    setInterval(loadTrends, 7000);
    </script>

    </body>
    </html>
    """)

# ---------------- DATA ----------------
@app.route("/api/data")
def get_data():
    return jsonify(data)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return {"ok": True}

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()