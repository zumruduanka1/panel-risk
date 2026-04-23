from flask import Flask, request, jsonify, render_template_string
import requests
import difflib
import smtplib
import os
import xml.etree.ElementTree as ET

app = Flask(__name__)

# ---------------- RSS ----------------
def parse_rss(url):
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)

        items = []
        for item in root.findall(".//item")[:15]:
            title = item.find("title").text
            items.append(title)

        return items
    except:
        return []

# ---------------- SOURCES ----------------
def get_sources():
    teyit = parse_rss("https://teyit.org/feed")
    dogruluk = parse_rss("https://www.dogrulukpayi.com/rss.xml")
    news = parse_rss("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr")

    return teyit + dogruluk + news

# ---------------- RISK ----------------
def analyze_text(text):
    score = 0
    reasons = []

    t = text.lower()

    # 1️⃣ kelime analizi
    keywords = ["şok","son dakika","inanılmaz","öldü","ifşa","gizli","acil"]
    for k in keywords:
        if k in t:
            score += 15
            reasons.append("Abartılı ifade")

    # 2️⃣ kaynak benzerliği
    sources = get_sources()
    matches = []
    for s in sources:
        ratio = difflib.SequenceMatcher(None, t, s.lower()).ratio()
        if ratio > 0.5:
            score += 20
            matches.append(s)

    if matches:
        reasons.append("Şüpheli içeriklerle benzer")

    # 3️⃣ kısa içerik
    if len(text) < 20:
        score += 10
        reasons.append("Kısa ve bağlamsız")

    return min(score,100), reasons, matches[:3]

# ---------------- EMAIL ----------------
def send_email(to, risk, text):
    try:
        sender = os.getenv("tubitaktest0@gmail.com")
        password = os.getenv("umdyxtmpeljhodhy")

        if not sender or not password:
            print("EMAIL ENV YOK")
            return

        msg = f"""Subject: Yüksek Risk Uyarısı

Girilen metin yüksek risk içeriyor!

Metin:
{text}

Risk: {risk}
"""

        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(sender, password)
        s.sendmail(sender, to, msg)
        s.quit()

        print("MAIL GÖNDERİLDİ")

    except Exception as e:
        print("mail hata:", e)

# ---------------- API ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text","")

    risk, reasons, matches = analyze_text(text)

    if risk > 70:
        send_email("rumeyysauslu@gmail.com", risk, text)

    return {
        "risk": risk,
        "reasons": reasons,
        "matches": matches
    }

# ---------------- UI ----------------
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Yalan Haber Analiz</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body {background:#0f172a;color:white;font-family:Arial;padding:20px;}
.card {background:#1e293b;padding:10px;margin:5px;border-radius:8px;}
.match {border-left:4px solid red;}
</style>
</head>

<body>

<h1>🚨 Yalan Haber Analiz</h1>

<input id="txt" placeholder="Metin gir">
<button onclick="analyze()">Analiz</button>

<h2 id="risk"></h2>

<ul id="reasons"></ul>

<canvas id="chart"></canvas>

<h3>🔍 Benzer İçerikler</h3>
<div id="matches"></div>

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

    let rhtml="";
    j.reasons.forEach(x=>{
        rhtml+="<li>"+x+"</li>";
    });
    document.getElementById("reasons").innerHTML=rhtml;

    let mhtml="";
    j.matches.forEach(x=>{
        mhtml+="<div class='card match'>"+x+"</div>";
    });
    document.getElementById("matches").innerHTML=mhtml;

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
</script>

</body>
</html>
""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()