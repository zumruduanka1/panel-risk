from flask import Flask, request, jsonify, render_template_string
import requests
import difflib
import xml.etree.ElementTree as ET
import smtplib
import os
import hashlib

app = Flask(__name__)

# ---------------- EMAIL ----------------
def send_email(subject, content):
    try:
        sender = os.getenv("tubitaktest0@gmail.com")
        password = os.getenv("umdyxtmpeljhodhy")
        receiver = os.getenv("rumeyysauslu@gmail.com")

        if not sender or not password or not receiver:
            print("EMAIL ENV eksik")
            return

        msg = f"Subject: {subject}\n\n{content}"

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
            title = item.find("title").text
            if title:
                data.append(title)

        return data
    except:
        return []

# ---------------- KAYNAKLAR ----------------
def get_news():
    return (
        parse_rss("https://teyit.org/feed") +
        parse_rss("https://www.dogrulukpayi.com/rss.xml") +
        parse_rss("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr")
    )

# ---------------- HABER Mİ ----------------
def is_news_like(text):
    keywords = ["haber","son dakika","iddia","paylaş","gündem"]
    return any(k in text.lower() for k in keywords)

# ---------------- RISK ----------------
def calc_risk(text):
    if not is_news_like(text):
        return 0, ["Haber formatı değil"]

    score = 0
    reasons = []
    t = text.lower()

    viral = ["şok","inanılmaz","öldü","ifşa","gizli","acil","hemen paylaş"]

    for w in viral:
        if w in t:
            score += 20
            reasons.append("Sosyal medya abartı dili")

    if "!" in text or text.isupper():
        score += 10
        reasons.append("Clickbait")

    if len(text) < 30:
        score += 10
        reasons.append("Kısa içerik")

    # kaynak benzerliği
    for s in get_news():
        ratio = difflib.SequenceMatcher(None, t, s.lower()).ratio()
        if ratio > 0.5:
            score += 20
            reasons.append("Şüpheli içerik benzerliği")
            break

    return min(score, 100), reasons

# ---------------- MAIL SPAM ENGEL ----------------
sent_cache = set()

def send_if_high_risk(title, risk):
    if risk < 80:
        return

    key = hashlib.md5(title.encode()).hexdigest()

    if key in sent_cache:
        return

    send_email(
        "🚨 Yüksek Riskli Haber",
        f"Haber:\n{title}\n\nRisk: {risk}"
    )

    sent_cache.add(key)

# ---------------- KAYNAK ANALİZ ----------------
def analyze_news():
    news = get_news()
    result = []

    for n in news[:25]:
        risk, reasons = calc_risk(n)

        if risk >= 50:  # ✅ BURASI DEĞİŞTİ
            result.append({
                "title": n,
                "risk": risk,
                "reasons": reasons
            })

            # 🔴 sadece 80+ mail
            send_if_high_risk(n, risk)

    return result

# ---------------- API ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text","")
    risk, reasons = calc_risk(text)

    if risk >= 80:
        send_email(
            "🚨 Kullanıcı Yüksek Riskli İçerik",
            f"Metin:\n{text}\n\nRisk: {risk}"
        )

    return {"risk": risk, "reasons": reasons}

@app.route("/api/news")
def news():
    return {"data": analyze_news()}

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
.card {background:#1e293b;padding:10px;margin:8px;border-radius:8px;}
.high {border-left:5px solid red;}
.medium {border-left:5px solid orange;}
input {padding:8px;width:260px;}
button {padding:8px;background:red;color:white;border:none;}
canvas {max-width:220px;margin-top:10px;}
</style>
</head>

<body>

<h2>🚨 Yalan Haber Risk Paneli</h2>

<input id="txt" placeholder="Haber gir">
<button onclick="analyze()">Analiz</button>

<h3 id="risk"></h3>
<ul id="reasons"></ul>

<canvas id="chart"></canvas>

<h3>🔥 Riskli Kaynak Haberler (50+)</h3>
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
    j.reasons.forEach(x=>{
        html+="<li>"+x+"</li>";
    });
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

    let html="";
    j.data.forEach(n=>{
        let cls = n.risk >= 80 ? "high" : "medium";

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

setInterval(loadNews,7000);
loadNews();

</script>

</body>
</html>
""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()