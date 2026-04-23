from flask import Flask, request, jsonify, render_template_string
import requests
import difflib
import xml.etree.ElementTree as ET
import smtplib
import os
import hashlib
import threading
import time

app = Flask(__name__)

news_cache = []
sent_cache = set()

# ---------------- EMAIL ----------------
def send_email(title, risk):
    try:
        sender = os.getenv("tubitaktest0@gmail.com")
        password = os.getenv("umdyxtmpeljhodhy")
        receiver = os.getenv("rumeyysauslu@gmail.com")

        if not sender or not password or not receiver:
            print("EMAIL ENV eksik")
            return

        msg = f"""Subject: 🚨 Yüksek Riskli Haber

Haber:
{title}

Risk: {risk}
"""

        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(sender, password)
        s.sendmail(sender, receiver, msg)
        s.quit()

        print("MAIL GÖNDERİLDİ")

    except Exception as e:
        print("mail hata:", e)

# ---------------- RSS ----------------
def parse_rss(url):
    try:
        r = requests.get(url, timeout=6)
        root = ET.fromstring(r.content)

        data = []
        for item in root.findall(".//item")[:20]:
            title = item.find("title")
            if title is not None and title.text:
                data.append(title.text)

        return data
    except:
        return []

# ---------------- REDDIT (SOSYAL MEDYA BENZERİ) ----------------
def get_reddit():
    try:
        r = requests.get(
            "https://www.reddit.com/r/news.json",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5
        ).json()

        return [p["data"]["title"] for p in r["data"]["children"][:20]]
    except:
        return []

# ---------------- TÜM KAYNAKLAR ----------------
def get_sources():
    data = []
    data += parse_rss("https://teyit.org/feed")
    data += parse_rss("https://www.dogrulukpayi.com/rss.xml")
    data += parse_rss("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr")
    data += get_reddit()

    # fallback
    if len(data) < 5:
        data += [
            "SON DAKİKA ŞOK HABER HERKES PAYLAŞIYOR",
            "İnanılmaz gizli gerçek ortaya çıktı",
            "Herkes bunu konuşuyor büyük iddia"
        ]

    return data

# ---------------- HABER Mİ ----------------
def is_news_like(text):
    keys = ["haber","son dakika","iddia","paylaş","gündem"]
    return any(k in text.lower() for k in keys)

# ---------------- RISK ----------------
def calc_risk(text):
    if not is_news_like(text):
        return 0, ["Haber formatı değil"]

    score = 20
    reasons = []
    t = text.lower()

    viral = ["şok","inanılmaz","öldü","ifşa","gizli","acil","hemen paylaş"]

    for w in viral:
        if w in t:
            score += 15
            reasons.append("Sosyal medya abartı dili")

    if "!" in text:
        score += 10
        reasons.append("Clickbait")

    if len(text) < 30:
        score += 10
        reasons.append("Kısa içerik")

    return min(score,100), reasons

# ---------------- BACKGROUND TARAYICI ----------------
def background_worker():
    global news_cache

    while True:
        sources = get_sources()
        result = []

        for n in sources:
            risk, reasons = calc_risk(n)

            if risk >= 50:
                result.append({
                    "title": n,
                    "risk": risk,
                    "reasons": reasons
                })

                # 🔴 80+ mail
                if risk >= 80:
                    key = hashlib.md5(n.encode()).hexdigest()
                    if key not in sent_cache:
                        send_email(n, risk)
                        sent_cache.add(key)

        news_cache = result[:20]

        time.sleep(60)  # 1 dk güncelle

# thread başlat
threading.Thread(target=background_worker, daemon=True).start()

# ---------------- API ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text","")
    risk, reasons = calc_risk(text)

    if risk >= 80:
        send_email(text, risk)

    return {"risk": risk, "reasons": reasons}

@app.route("/api/news")
def news():
    return {"data": news_cache}

# ---------------- UI ----------------
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Fake News Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body {background:#0f172a;color:white;font-family:Arial;padding:20px;}
.card {background:#1e293b;padding:12px;margin:10px;border-radius:10px;}
.high {border-left:5px solid red;}
.medium {border-left:5px solid orange;}
.box {display:flex;gap:20px;}
.stat {background:#111827;padding:15px;border-radius:8px;}
canvas {max-width:200px;}
</style>
</head>

<body>

<h1>🚨 Yalan Haber Dashboard</h1>

<div class="box">
  <div class="stat">Toplam: <span id="total">0</span></div>
  <div class="stat">80+ Risk: <span id="high">0</span></div>
</div>

<br>

<input id="txt" placeholder="Haber gir">
<button onclick="analyze()">Analiz</button>

<h3 id="risk"></h3>
<ul id="reasons"></ul>

<canvas id="chart"></canvas>

<h2>🔥 Riskli Haberler</h2>
<div id="news"></div>

<script>
let chart;

async function analyze(){
    let t=document.getElementById("txt").value;

    let r=await fetch("/api/analyze",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({text:t})
    });

    let j=await r.json();

    document.getElementById("risk").innerText="Risk: "+j.risk;

    let html="";
    j.reasons.forEach(x=> html+="<li>"+x+"</li>");
    document.getElementById("reasons").innerHTML=html;

    draw(j.risk);
}

function draw(r){
    if(chart) chart.destroy();

    chart=new Chart(document.getElementById("chart"),{
        type:"doughnut",
        data:{
            labels:["Risk","Safe"],
            datasets:[{data:[r,100-r]}]
        }
    });
}

async function loadNews(){
    let r=await fetch("/api/news");
    let j=await r.json();

    let total=j.data.length;
    let high=j.data.filter(x=>x.risk>=80).length;

    document.getElementById("total").innerText=total;
    document.getElementById("high").innerText=high;

    let html="";
    j.data.forEach(n=>{
        let cls=n.risk>=80?"high":"medium";

        html+=`
        <div class="card ${cls}">
            <b>${n.title}</b><br>
            Risk: ${n.risk}<br>
            ${n.reasons.join(", ")}
        </div>
        `;
    });

    document.getElementById("news").innerHTML=html;
}

setInterval(loadNews,5000);
loadNews();

</script>

</body>
</html>
""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()