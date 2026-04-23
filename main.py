from flask import Flask, request, jsonify, render_template_string
import requests
import difflib
import xml.etree.ElementTree as ET
import smtplib
import os

app = Flask(__name__)

# ---------------- EMAIL ----------------
def send_email(content):
    try:
        sender = os.getenv("tubitaktest0@gmail.com")
        password = os.getenv("umdyxtmpeljhodhy")

        if not sender or not password:
            print("Email ayarlanmadı")
            return

        msg = f"""Subject: 🚨 Yüksek Riskli Haber Bulundu

Aşağıdaki içerik yüksek riskli:

{content}
"""

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, "rumeyysauslu@gmail.com", msg)
        server.quit()

        print("MAIL GÖNDERİLDİ")

    except Exception as e:
        print("Mail hata:", e)

# ---------------- RSS ----------------
def parse_rss(url):
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)

        data = []
        for item in root.findall(".//item")[:20]:
            title = item.find("title").text
            data.append(title)

        return data
    except:
        return []

# ---------------- KAYNAKLAR ----------------
def get_news():
    teyit = parse_rss("https://teyit.org/feed")
    dogruluk = parse_rss("https://www.dogrulukpayi.com/rss.xml")
    google = parse_rss("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr")

    return teyit + dogruluk + google

# ---------------- RISK ----------------
def calc_risk(text):
    score = 0
    reasons = []

    t = text.lower()

    viral = [
        "şok","son dakika","inanılmaz","öldü",
        "ifşa","gizli","acil","hemen paylaş",
        "herkes bunu konuşuyor"
    ]

    for w in viral:
        if w in t:
            score += 15
            reasons.append("Abartı / sosyal medya dili")

    if "!" in text or text.isupper():
        score += 10
        reasons.append("Clickbait")

    if len(text) < 25:
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

# ---------------- KAYNAK ANALİZ ----------------
def analyze_news():
    news = get_news()
    result = []

    for n in news[:15]:
        risk, reasons = calc_risk(n)

        if risk > 60:
            result.append({
                "title": n,
                "risk": risk,
                "reasons": reasons
            })

            # 🔴 yüksek riskte mail
            if risk > 80:
                send_email(n)

    return result

# ---------------- API ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text","")
    risk, reasons = calc_risk(text)

    if risk > 80:
        send_email(text)

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
.card {background:#1e293b;padding:10px;margin:10px;border-radius:8px;}
.high {border-left:5px solid red;}
.medium {border-left:5px solid orange;}
input {padding:10px;width:300px;}
button {padding:10px;background:red;color:white;border:none;}
</style>
</head>

<body>

<h1>🚨 Sosyal Medya Yalan Haber Paneli</h1>

<input id="txt" placeholder="Metin gir">
<button onclick="analyze()">Analiz</button>

<h2 id="risk"></h2>
<ul id="reasons"></ul>

<canvas id="chart"></canvas>

<h2>🔥 Yüksek Riskli Haberler</h2>
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
        let cls = n.risk > 80 ? "high" : "medium";

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