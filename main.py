from flask import Flask, request, jsonify, render_template_string
import requests
import smtplib
import os
import xml.etree.ElementTree as ET

app = Flask(__name__)

# ---------------- RISK ENGINE ----------------
def fake_score(text):
    score = 0
    t = text.lower()

    strong = [
        "şok","son dakika","inanılmaz","öldü",
        "ifşa","gizli","kanıtlandı","herkes bunu konuşuyor",
        "acil","hemen paylaş","büyük skandal"
    ]

    for k in strong:
        if k in t:
            score += 20

    if text.isupper():
        score += 20

    if len(text) < 20:
        score += 10

    return min(score,100)

# ---------------- EMAIL ----------------
def send_email():
    try:
        sender = os.getenv("tubitaktest0@gmail.com")
        password = os.getenv("umdyxtmpeljhodhy")

        if not sender or not password:
            print("MAIL ENV YOK")
            return

        msg = "Subject: Yüksek Risk!\n\nRiskli içerik tespit edildi!"

        s = smtplib.SMTP("smtp.gmail.com",587)
        s.starttls()
        s.login(sender,password)
        s.sendmail(sender,"rumeyysauslu@gmail.com",msg)
        s.quit()

    except Exception as e:
        print(e)

# ---------------- USER ANALYZE ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text","")
    risk = fake_score(text)

    if risk > 70:
        send_email()

    return {"risk":risk}

# ---------------- RSS PARSER ----------------
def rss(url):
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)

        data = []
        for item in root.findall(".//item")[:10]:
            title = item.find("title").text
            risk = fake_score(title)

            if risk > 60:
                data.append({"title":title,"risk":risk})

        return data
    except:
        return []

# ---------------- SOURCES ----------------
@app.route("/api/teyit")
def teyit():
    return {"data": rss("https://teyit.org/feed")}

@app.route("/api/dogruluk")
def dogruluk():
    return {"data": rss("https://www.dogrulukpayi.com/rss.xml")}

@app.route("/api/news")
def news():
    return {"data": rss("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr")}

@app.route("/api/trends")
def trends():
    try:
        r = requests.get("https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR")
        root = ET.fromstring(r.content)

        t = []
        for item in root.findall(".//item")[:10]:
            t.append(item.find("title").text)

        return {"data":t}
    except:
        return {"data":[]}

# ---------------- UI ----------------
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Yalan Haber Paneli</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body {background:#0f172a;color:white;font-family:Arial;padding:20px;}
.card {background:#1e293b;padding:10px;margin:5px;border-radius:8px;}
.high {border-left:5px solid red;}
input {padding:10px;width:300px;}
button {padding:10px;background:red;color:white;border:none;}
</style>
</head>

<body>

<h1>🚨 Yalan Haber Risk Paneli</h1>

<input id="txt" placeholder="Metin gir">
<button onclick="analyze()">Analiz</button>

<h2 id="risk"></h2>

<canvas id="chart"></canvas>

<h2>📊 Teyit</h2>
<div id="teyit"></div>

<h2>📊 Doğruluk Payı</h2>
<div id="dogruluk"></div>

<h2>📰 Haberler</h2>
<div id="news"></div>

<h2>🔥 Trendler</h2>
<div id="trends"></div>

<script>
let chart;

function draw(r){
    if(chart) chart.destroy();

    chart=new Chart(document.getElementById("chart"),{
        type:"bar",
        data:{labels:["Risk"],datasets:[{data:[r]}]}
    });
}

async function analyze(){
    let t=document.getElementById("txt").value;

    let r=await fetch("/api/analyze",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({text:t})
    });

    let j=await r.json();

    document.getElementById("risk").innerText="Risk: "+j.risk;

    draw(j.risk);
}

async function load(url,id){
    let r=await fetch(url);
    let j=await r.json();

    let html="";
    j.data.forEach(i=>{
        html+="<div class='card high'>"+(i.title||i)+"</div>";
    });

    document.getElementById(id).innerHTML=html;
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