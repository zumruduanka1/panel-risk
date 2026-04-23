from flask import Flask, request, jsonify, render_template_string
import requests
import difflib
import xml.etree.ElementTree as ET

app = Flask(__name__)

# ---------------- RSS PARSER ----------------
def parse_rss(url):
    try:
        r = requests.get(url, timeout=6)
        root = ET.fromstring(r.content)

        data = []
        for item in root.findall(".//item"):
            title = item.find("title")
            if title is not None and title.text:
                data.append(title.text)

        return data[:30]
    except:
        return []

# ---------------- KAYNAKLAR ----------------
def get_news():
    sources = []

    sources += parse_rss("https://teyit.org/feed")
    sources += parse_rss("https://www.dogrulukpayi.com/rss.xml")
    sources += parse_rss("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr")

    # fallback (boş gelirse)
    if len(sources) < 5:
        sources += [
            "SON DAKİKA ŞOK HABER HERKES PAYLAŞIYOR",
            "İnanılmaz olay gizli gerçek ortaya çıktı",
            "Herkes bunu konuşuyor büyük iddia",
            "Acil paylaşılması gereken haber",
        ]

    return sources

# ---------------- HABER Mİ ----------------
def is_news_like(text):
    keywords = ["haber","son dakika","iddia","paylaş","gündem","açıklama"]
    return any(k in text.lower() for k in keywords)

# ---------------- RISK ----------------
def calc_risk(text):
    if not is_news_like(text):
        return 0, ["Haber formatı değil"]

    score = 20  # taban

    reasons = []
    t = text.lower()

    viral = ["şok","inanılmaz","öldü","ifşa","gizli","acil"]

    for w in viral:
        if w in t:
            score += 15
            reasons.append("Abartı / viral dil")

    if "!" in text:
        score += 10
        reasons.append("Clickbait")

    if len(text) < 30:
        score += 10
        reasons.append("Kısa içerik")

    return min(score, 100), reasons

# ---------------- KAYNAK ANALİZ ----------------
def analyze_news():
    news = get_news()
    result = []

    for n in news:
        risk, reasons = calc_risk(n)

        if risk >= 50:
            result.append({
                "title": n,
                "risk": risk,
                "reasons": reasons
            })

    return result[:15]

# ---------------- API ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text","")
    risk, reasons = calc_risk(text)
    return {"risk": risk, "reasons": reasons}

@app.route("/api/news")
def news():
    return {"data": analyze_news()}

# ---------------- DASHBOARD UI ----------------
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Yalan Haber Dashboard</title>
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
  <div class="stat">Toplam Haber: <span id="total">0</span></div>
  <div class="stat">Yüksek Risk: <span id="high">0</span></div>
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

    let total = j.data.length;
    let high = j.data.filter(x=>x.risk>=80).length;

    document.getElementById("total").innerText = total;
    document.getElementById("high").innerText = high;

    let html="";
    j.data.forEach(n=>{
        let cls = n.risk>=80 ? "high" : "medium";

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