from flask import Flask, jsonify, request, render_template_string
import requests
import difflib
import smtplib
import os

app = Flask(__name__)

data = {"news": []}

# ---------------- RISK SCORE ----------------
def fake_score(text):
    score = 0
    text = text.lower()

    keywords = [
        "şok", "son dakika", "inanılmaz", "öldü",
        "ifşa", "gizli", "gizemli", "şok edici",
        "kanıtlandı", "herkes bunu konuşuyor"
    ]

    for k in keywords:
        if k in text:
            score += 15

    if text.isupper():
        score += 20

    if len(text) < 25:
        score += 10

    return min(score, 100)

# ---------------- EMAIL ----------------
def send_email(to):
    try:
        sender = os.getenv("tubitaktest0@gmail.com")
        password = os.getenv("umdyxtmpeljhodhy")

        if not sender or not password:
            print("Email env tanımlı değil")
            return

        message = "Subject: Risk Uyarısı\n\nYüksek riskli içerik tespit edildi!"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, to, message)
        server.quit()

    except Exception as e:
        print("mail hata:", e)

# ---------------- ANALYZE ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text", "")
    score = fake_score(text)

    result = {"text": text, "risk": score}
    data["news"].append(result)

    if score > 70:
        send_email("rumeyysauslu@gmail.com")

    return result

# ---------------- NEWS ----------------
@app.route("/api/news")
def news():
    api_key = os.getenv("NEWS_API_KEY")
    url = f"https://newsapi.org/v2/top-headlines?country=tr&apiKey={api_key}"

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

# ---------------- GOOGLE TRENDS ----------------
@app.route("/api/trends")
def trends():
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR"

    try:
        res = requests.get(url).text
        items = res.split("<title>")[1:10]

        trend_list = []
        for i in items:
            trend_list.append(i.split("</title>")[0])

        return {"trends": trend_list}
    except:
        return {"trends": []}

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    return render_template_string("""
    <h1>Sosyal Medya Risk Paneli</h1>

    <input id="txt" placeholder="Haber gir">
    <button onclick="analyze()">Analiz</button>

    <p id="res"></p>

    <h2>Türkçe Haberler</h2>
    <div id="news"></div>

    <h2>Trendler</h2>
    <div id="trends"></div>

    <script>
    async function analyze(){
        let t = document.getElementById("txt").value;

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
            html += "<p>"+n.title+" → "+n.risk+"</p>";
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

    setInterval(loadNews, 5000);
    setInterval(loadTrends, 7000);
    </script>
    """)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return {"ok": True}

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()