from flask import Flask, request, jsonify, render_template_string
import requests
import smtplib
import os
import xml.etree.ElementTree as ET

app = Flask(__name__)

# ---------------- RISK ----------------
def fake_score(text):
    score = 0
    t = text.lower()

    keywords = [
        "şok","son dakika","inanılmaz","öldü",
        "ifşa","gizli","kanıtlandı",
        "herkes bunu konuşuyor","acil","hemen paylaş"
    ]

    for k in keywords:
        if k in t:
            score += 20

    if text.isupper():
        score += 20

    if len(text) < 20:
        score += 10

    return min(score, 100)

# ---------------- EMAIL ----------------
def send_email(to):
    try:
        sender = os.getenv("tubitaktest0@gmail.com")
        password = os.getenv("umdyxtmpeljhodhy")

        if not sender or not password:
            print("EMAIL ENV YOK")
            return

        msg = "Subject: Risk Uyarısı\n\nYüksek riskli içerik bulundu!"

        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(sender, password)
        s.sendmail(sender, to, msg)
        s.quit()

        print("MAIL GÖNDERİLDİ")

    except Exception as e:
        print("mail hata:", e)

# ---------------- ANALYZE ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text", "")
    risk = fake_score(text)

    if risk > 70:
        send_email("rumeyysauslu@gmail.com")

    return {"risk": risk}

# ---------------- RSS PARSER ----------------
def parse_rss(url):
    try:
        res = requests.get(url, timeout=5)
        root = ET.fromstring(res.content)

        items = []
        for item in root.findall(".//item")[:10]:
            title = item.find("title").text
            r = fake_score(title)

            if r > 60:
                items.append({"title": title, "risk": r})

        return items
    except:
        return []

# ---------------- ENDPOINTS ----------------
@app.route("/api/teyit")
def teyit():
    return {"data": parse_rss("https://teyit.org/feed")}

@app.route("/api/dogruluk")
def dogruluk():
    return {"data": parse_rss("https://www.dogrulukpayi.com/rss.xml")}

@app.route("/api/news")
def news():
    return {"data": parse_rss("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr")}

@app.route("/api/trends")
def trends():
    try:
        res = requests.get("https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR")
        root = ET.fromstring(res.content)

        trends = []
        for item in root.findall(".//item")[:10]:
            trends.append(item.find("title").text)

        return {"data": trends}
    except:
        return {"data":[]}

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
body {background:#0f172a;color:white;font-family:Arial;padding:20px;}
.card {background:#1e293b;padding:10px;margin:5px;border-radius:8px;}
.high {border-left:4px solid red;}
</style>
</head>

<body>

<h1>🚨 Risk Panel</h1>

<input id="txt" placeholder="Haber gir">
<button onclick="analyze()">Analiz</button>

<h2 id="risk"></h2>

<canvas id="chart" height="100"></canvas>

<h2>Teyit</h2>
<div id="teyit"></div>

<h2>Doğruluk</h2>
<div id="dogruluk"></div>

<h2>Haberler</h2>
<div id="news"></div>

<h2>Trendler</h2>
<div id="trends"></div>

<script>
let chart;

function draw(r){
    const ctx = document.getElementById("chart");

    if(chart) chart.destroy();

    chart = new Chart(ctx,{
        type:"bar",
        data:{
            labels:["Risk"],
            datasets:[{label:"Risk",data:[r]}]
        }
    });
}

async function analyze(){
    let t = document.getElementById("txt").value;

    let r = await fetch("/api/analyze",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({text:t})
    });

    let j = await r.json();

    document.getElementById("risk").innerText="Risk: "+j.risk;

    draw(j.risk);
}

async function load(url,id){
    let r = await fetch(url);
    let j = await r.json();

    let html="";
    j.data.forEach(i=>{
        html += "<div class='card high'>"+(i.title||i)+"</div>";
    });

    document.getElementById(id).innerHTML = html;
}

setInterval(()=>load("/api/teyit","teyit"),5000);
setInterval(()=>load("/api/dogruluk","dogruluk"),6000);
setInterval(()=>load("/api/news","news"),7000);
setInterval(()=>load("/api/trends","trends"),8000);

load("/api/teyit","teyit");
load("/api/dogruluk","dogruluk");
load("/api/news","news");
load("/api/trends","trends");
</script>

</body>
</html>
""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()