from flask import Flask, request, jsonify, render_template_string
import requests, smtplib, os, hashlib, time
import xml.etree.ElementTree as ET

app = Flask(__name__)

news_cache = []
stats = {"total": 0, "high": 0}
last_update = 0
sent = set()

# ---------------- EMAIL ----------------
def send_email(text, risk):
    try:
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(os.getenv("tubitaktest0@gmail.com"), os.getenv("umdyxtmpeljhodhy"))
        msg = f"Subject: 🚨 Yüksek Risk\n\n{text}\nRisk: {risk}"
        s.sendmail(os.getenv("tubitaktest0@gmail.com"), os.getenv("rumeyysauslu@gmail.com"), msg)
        s.quit()
    except:
        pass

# ---------------- RSS ----------------
def parse(url):
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)
        return [i.find("title").text for i in root.findall(".//item")[:20]]
    except:
        return []

# ---------------- YALAN HABER KAYNAKLARI ----------------
def get_news():
    data = []

    # teyit siteleri (en önemli)
    data += parse("https://teyit.org/feed")
    data += parse("https://www.dogrulukpayi.com/rss.xml")
    data += parse("https://malumatfurus.org/feed")

    # sosyal medya etkisi
    data += parse("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr")

    # fallback
    if len(data) < 5:
        data += [
            "ŞOK HABER herkes paylaşıyor gizli gerçek ortaya çıktı",
            "ACİL bu haberi silmeden önce oku",
            "İnanılmaz olay sosyal medyada yayıldı"
        ]

    return data

# ---------------- RISK ----------------
def calc_risk(text):
    score = 30
    t = text.lower()

    viral = ["şok","inanılmaz","acil","ifşa","gizli","iddia","herkes"]

    for v in viral:
        if v in t:
            score += 15

    if "!" in text:
        score += 10

    if len(text) < 40:
        score += 10

    return min(score, 100)

# ---------------- REFRESH ----------------
def refresh():
    global news_cache, stats, last_update

    if time.time() - last_update < 30:
        return

    last_update = time.time()

    data = []
    total = 0
    high = 0

    for n in get_news():
        r = calc_risk(n)
        total += 1

        if r >= 50:
            data.append({"title": n, "risk": r})

        if r >= 80:
            high += 1
            key = hashlib.md5(n.encode()).hexdigest()
            if key not in sent:
                send_email(n, r)
                sent.add(key)

    news_cache = data[:20]
    stats = {"total": total, "high": high}

# ---------------- API ----------------
@app.route("/api/news")
def news():
    refresh()
    return {"data": news_cache, "stats": stats}

@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text")
    r = calc_risk(text)

    if r >= 80:
        send_email(text, r)

    return {"risk": r}

# ---------------- UI ----------------
@app.route("/")
def home():
    return render_template_string("""
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body {background:#0f172a;color:white;font-family:Arial;padding:20px;}
.card {background:#1e293b;padding:10px;margin:10px;border-radius:10px;}
</style>
</head>

<body>

<h1>🚨 Yalan Haber Paneli</h1>

<p>Analiz: <span id="t">0</span> | 80+: <span id="h">0</span></p>

<input id="txt">
<button onclick="a()">Analiz</button>

<h3 id="r"></h3>
<canvas id="c"></canvas>

<h2>🔥 Yüksek Riskli Haberler</h2>
<div id="news"></div>

<script>
let chart;

async function a(){
 let t=document.getElementById("txt").value;

 let r=await fetch("/api/analyze",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({text:t})
 });

 let j=await r.json();

 document.getElementById("r").innerText="Risk:"+j.risk;

 if(chart) chart.destroy();
 chart=new Chart(c,{
  type:"doughnut",
  data:{labels:["risk","safe"],datasets:[{data:[j.risk,100-j.risk]}]}
 });
}

async function load(){
 let r=await fetch("/api/news");
 let j=await r.json();

 t.innerText=j.stats.total;
 h.innerText=j.stats.high;

 let html="";
 j.data.forEach(n=>{
  html+=`<div class="card">${n.title}<br>Risk:${n.risk}</div>`;
 });

 news.innerHTML=html;
}

setInterval(load,5000);
load();
</script>

</body>
</html>
""")

app.run()