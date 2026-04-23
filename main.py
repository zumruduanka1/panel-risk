from flask import Flask, request, jsonify, render_template_string
import requests
import smtplib
import os
from datetime import datetime

app = Flask(__name__)

history = []

# ---------------- RISK ENGINE ----------------
def fake_score(text):
    score = 0
    t = text.lower()

    keywords = [
        "şok", "son dakika", "inanılmaz", "öldü",
        "ifşa", "gizli", "gizemli", "şok edici",
        "kanıtlandı", "herkes bunu konuşuyor",
        "hemen paylaş", "çok acil"
    ]

    for k in keywords:
        if k in t:
            score += 15

    if text.isupper():
        score += 20

    if len(text) < 20:
        score += 10

    # tekrar içerik (spam hissi)
    for h in history[-10:]:
        if t in h["text"].lower():
            score += 10

    return min(score, 100)

# ---------------- EMAIL ----------------
def send_email(to):
    try:
        sender = os.getenv("tubitaktest0@gmail.com")
        password = os.getenv("umdyxtmpeljhodhy")
        if not sender or not password:
            return

        msg = f"Subject: Risk Uyarısı\n\nYüksek riskli içerik bulundu! {datetime.now()}"

        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(sender, password)
        s.sendmail(sender, to, msg)
        s.quit()
    except Exception as e:
        print("mail hata:", e)

# ---------------- ANALYZE ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text", "")
    score = fake_score(text)

    history.append({"text": text, "risk": score})

    if score > 70:
        send_email("rumeyysauslu@gmail.com")

    return {"risk": score}

# ---------------- GOOGLE NEWS (TR) ----------------
@app.route("/api/news")
def news():
    try:
        url = "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr"
        xml = requests.get(url).text
        items = xml.split("<title>")[1:8]

        news_list = []
        for i in items:
            title = i.split("</title>")[0]
            news_list.append({
                "title": title,
                "risk": fake_score(title)
            })

        return {"news": news_list}
    except:
        return {"news": []}

# ---------------- REDDIT (PUBLIC) ----------------
@app.route("/api/social")
def social():
    try:
        url = "https://www.reddit.com/r/Turkey/.rss"
        xml = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
        items = xml.split("<title>")[2:8]

        data = []
        for i in items:
            title = i.split("</title>")[0]
            data.append({
                "title": title,
                "risk": fake_score(title)
            })

        return {"social": data}
    except:
        return {"social": []}

# ---------------- TRENDS ----------------
@app.route("/api/trends")
def trends():
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR"
        xml = requests.get(url).text
        items = xml.split("<title>")[1:10]
        return {"trends": [i.split("</title>")[0] for i in items]}
    except:
        return {"trends": []}

# ---------------- UI ----------------
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Risk Paneli</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body {
    background:#0f172a;
    color:white;
    font-family:Arial;
    padding:20px;
}

input {
    padding:10px;
    width:300px;
}

button {
    padding:10px;
    background:#3b82f6;
    color:white;
    border:none;
    cursor:pointer;
}

.card {
    background:#1e293b;
    padding:15px;
    margin:10px 0;
    border-radius:10px;
}

.high {color:#ef4444;}
.mid {color:#facc15;}
.low {color:#22c55e;}
</style>
</head>

<body>

<h1>🚨 Sosyal Medya Risk Paneli</h1>

<input id="txt" placeholder="Haber gir">
<button onclick="analyze()">Analiz</button>

<h2 id="risk"></h2>

<canvas id="chart"></canvas>

<h2>📰 Haberler</h2>
<div id="news"></div>

<h2>🌐 Sosyal Medya</h2>
<div id="social"></div>

<h2>🔥 Trendler</h2>
<div id="trends"></div>

<script>
let chart;

function riskClass(r){
    if(r>70) return "high";
    if(r>40) return "mid";
    return "low";
}

async function analyze(){
    let t = document.getElementById("txt").value;

    let r = await fetch("/api/analyze",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({text:t})
    });

    let j = await r.json();

    document.getElementById("risk").innerHTML =
        "Risk: <span class='"+riskClass(j.risk)+"'>"+j.risk+"</span>";

    draw(j.risk);
}

function draw(val){
    let ctx = document.getElementById("chart");

    if(chart) chart.destroy();

    chart = new Chart(ctx,{
        type:"bar",
        data:{
            labels:["Risk"],
            datasets:[{label:"Risk", data:[val]}]
        }
    });
}

async function load(url, target){
    let r = await fetch(url);
    let j = await r.json();

    let key = Object.keys(j)[0];
    let html = "";

    j[key].forEach(i=>{
        html += `<div class="card ${riskClass(i.risk||0)}">
        ${i.title} → ${i.risk||""}
        </div>`;
    });

    document.getElementById(target).innerHTML = html;
}

load("/api/news","news");
load("/api/social","social");
load("/api/trends","trends");
</script>

</body>
</html>
""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()