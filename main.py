from flask import Flask, request, jsonify, render_template_string
import requests
import os
import smtplib
from datetime import datetime

app = Flask(__name__)

history = []

# ---------------- RISK ENGINE ----------------
def fake_score(text):
    score = 0
    t = text.lower()

    strong_words = [
        "şok","son dakika","inanılmaz","öldü","ifşa",
        "gizli","kanıtlandı","herkes bunu konuşuyor",
        "acil","hemen paylaş","büyük skandal"
    ]

    for w in strong_words:
        if w in t:
            score += 20

    if text.isupper():
        score += 20

    if len(text) < 20:
        score += 10

    return min(score,100)

# ---------------- EMAIL ----------------
def send_email(to):
    try:
        sender = os.getenv("tubitaktest0@gmail.com")
        password = os.getenv("umdyxtmpeljhodhy")

        if not sender or not password:
            return

        msg = "Subject: Yüksek Risk\n\nRiskli içerik bulundu!"

        s = smtplib.SMTP("smtp.gmail.com",587)
        s.starttls()
        s.login(sender,password)
        s.sendmail(sender,to,msg)
        s.quit()

    except Exception as e:
        print("mail hata:",e)

# ---------------- ANALYZE ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text","")
    score = fake_score(text)

    history.append(score)

    if score > 70:
        send_email("rumeyysauslu@gmail.com")

    return {"risk": score}

# ---------------- NEWS ----------------
@app.route("/api/news")
def news():
    try:
        url = "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr"
        xml = requests.get(url).text
        items = xml.split("<title>")[1:10]

        data = []
        for i in items:
            title = i.split("</title>")[0]
            r = fake_score(title)

            if r > 60:  # SADECE YÜKSEK RİSK
                data.append({"title": title, "risk": r})

        return {"news": data}
    except:
        return {"news":[]}

# ---------------- SOCIAL (reddit public) ----------------
@app.route("/api/social")
def social():
    try:
        url = "https://www.reddit.com/r/Turkey/.rss"
        xml = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}).text
        items = xml.split("<title>")[2:10]

        data = []
        for i in items:
            title = i.split("</title>")[0]
            r = fake_score(title)

            if r > 60:
                data.append({"title": title, "risk": r})

        return {"social": data}
    except:
        return {"social":[]}

# ---------------- TRENDS FIX ----------------
@app.route("/api/trends")
def trends():
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR"
        xml = requests.get(url).text
        items = xml.split("<title>")[1:10]

        return {"trends":[i.split("</title>")[0] for i in items]}
    except:
        return {"trends":[]}

# ---------------- UI ----------------
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Risk Panel</title>
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
    background:#ef4444;
    color:white;
    border:none;
}
.card {
    background:#1e293b;
    margin:10px 0;
    padding:15px;
    border-radius:10px;
}
.high {border-left:5px solid red;}
</style>
</head>

<body>

<h1>🚨 Yalan Haber Risk Paneli</h1>

<input id="txt" placeholder="Metin gir">
<button onclick="analyze()">Analiz</button>

<h2 id="risk"></h2>

<canvas id="chart1"></canvas>
<canvas id="chart2"></canvas>

<h2>📰 Yüksek Riskli Haberler</h2>
<div id="news"></div>

<h2>🌐 Sosyal Medya Benzeri</h2>
<div id="social"></div>

<h2>🔥 Trendler</h2>
<div id="trends"></div>

<script>
let chart1, chart2;

async function analyze(){
    let t=document.getElementById("txt").value;

    let r=await fetch("/api/analyze",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({text:t})
    });

    let j=await r.json();

    document.getElementById("risk").innerText="Risk: "+j.risk;

    drawCharts(j.risk);
}

function drawCharts(r){
    if(chart1) chart1.destroy();
    if(chart2) chart2.destroy();

    chart1=new Chart(document.getElementById("chart1"),{
        type:"bar",
        data:{
            labels:["Risk"],
            datasets:[{data:[r]}]
        }
    });

    chart2=new Chart(document.getElementById("chart2"),{
        type:"doughnut",
        data:{
            labels:["Risk","Safe"],
            datasets:[{data:[r,100-r]}]
        }
    });
}

async function load(url,id){
    let r=await fetch(url);
    let j=await r.json();

    let key=Object.keys(j)[0];

    let html="";
    j[key].forEach(i=>{
        html+=`<div class="card high">${i.title} → ${i.risk}</div>`;
    });

    document.getElementById(id).innerHTML=html;
}

async function loadTrends(){
    let r=await fetch("/api/trends");
    let j=await r.json();

    let html="";
    j.trends.forEach(t=>{
        html+=`<div class="card">${t}</div>`;
    });

    document.getElementById("trends").innerHTML=html;
}

setInterval(()=>load("/api/news","news"),5000);
setInterval(()=>load("/api/social","social"),6000);
setInterval(loadTrends,8000);

load("/api/news","news");
load("/api/social","social");
loadTrends();
</script>

</body>
</html>
""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()