from flask import Flask, request, jsonify, render_template_string
import requests, smtplib, os, time, hashlib
import xml.etree.ElementTree as ET

app = Flask(__name__)

cache = []
stats = {"total": 0, "danger": 0, "safe": 0}
sent = set()
last = 0

# ---------------- EMAIL ----------------
def send_email(text, risk):
    try:
        user = os.getenv("tubitaktest0@gmail.com")
        pw = os.getenv("umdyxtmpeljhodhy")
        to = os.getenv("rumeyysauslu@gmail.com")

        if not user or not pw or not to:
            return

        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(user, pw)

        msg = f"Subject: 🚨 Yüksek Risk\n\n{text}\nRisk: {risk}%"
        s.sendmail(user, to, msg)
        s.quit()
    except:
        pass

# ---------------- RSS ----------------
def parse(url):
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)
        return [i.find("title").text for i in root.findall(".//item")[:10]]
    except:
        return []

# ---------------- DATA ----------------
def social_sim():
    return [
        "site:x.com şok iddia hızla yayılıyor",
        "site:instagram.com inanılmaz olay ortaya çıktı",
        "site:tiktok.com gizli gerçek ifşa edildi"
    ]

def trends():
    try:
        r = requests.get("https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR").text
        return [i.split("</title>")[0] for i in r.split("<title>")[1:10]]
    except:
        return []

def collect():
    data = []
    data += parse("https://teyit.org/feed")
    data += parse("https://www.dogrulukpayi.com/rss.xml")
    data += parse("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr")
    data += trends()
    data += social_sim()
    return data

# ---------------- RISK ----------------
def risk_score(text):
    s = 30
    t = text.lower()

    keywords = ["şok","gizli","ifşa","iddia","herkes","yayılıyor"]

    for k in keywords:
        if k in t:
            s += 15

    if "!" in text:
        s += 10

    if len(text) < 40:
        s += 10

    return min(s,100)

# ---------------- REFRESH ----------------
def refresh():
    global cache, stats, last

    if time.time() - last < 20:
        return

    last = time.time()

    raw = collect()

    out = []
    total = 0
    danger = 0
    safe = 0

    for item in raw:
        r = risk_score(item)
        total += 1

        if r >= 50:
            out.append({"text": item, "risk": r})

        if r >= 80:
            danger += 1
            h = hashlib.md5(item.encode()).hexdigest()
            if h not in sent:
                send_email(item, r)
                sent.add(h)
        else:
            safe += 1

    cache = out[:20]
    stats = {"total": total, "danger": danger, "safe": safe}

# ---------------- API ----------------
@app.route("/api/news")
def news():
    refresh()
    return {"data": cache, "stats": stats}

@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text")
    r = risk_score(text)

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
body{background:#020617;color:white;font-family:Arial;padding:20px;}
.container{max-width:1100px;margin:auto;}
.title{text-align:center;font-size:40px;}
.stats{display:flex;justify-content:center;gap:20px;margin:20px;}
.box{background:#0f172a;padding:20px;border-radius:12px;width:150px;text-align:center;}
.panel{display:flex;gap:20px;}
.card{background:#0f172a;padding:20px;border-radius:12px;flex:1;}
input{width:100%;padding:10px;border-radius:10px;border:none;}
button{margin-top:10px;padding:10px;width:100%;background:#2563eb;border:none;border-radius:10px;color:white;}
.high{color:red;} .mid{color:orange;} .low{color:lightgreen;}
</style>
</head>

<body>
<div class="container">

<div class="title">AI Risk Dashboard</div>

<div class="stats">
<div class="box">Toplam<br><b id="t">0</b></div>
<div class="box">Tehlikeli<br><b id="d">0</b></div>
<div class="box">Güvenli<br><b id="s">0</b></div>
</div>

<div class="panel">

<div class="card">
<h3>Yeni Analiz</h3>
<input id="txt">
<button onclick="analyze()">Analiz</button>
<h3 id="res"></h3>
<canvas id="chart"></canvas>
</div>

<div class="card">
<h3>Filtre (Risk ≥ <span id="fval">50</span>)</h3>
<input type="range" min="0" max="100" value="50" id="filter" oninput="load()">
<h3>Haberler</h3>
<div id="news"></div>
<canvas id="bar"></canvas>
</div>

</div>

</div>

<script>
let donut, bar;

function color(r){
 if(r>=80) return "high";
 if(r>=50) return "mid";
 return "low";
}

async function analyze(){
 let t=document.getElementById("txt").value;

 let r=await fetch("/api/analyze",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({text:t})
 });

 let j=await r.json();

 res.innerHTML="Risk: <span class='"+color(j.risk)+"'>"+j.risk+"%</span>";

 if(donut) donut.destroy();

 donut=new Chart(chart,{
  type:"doughnut",
  data:{labels:["Risk","Safe"],datasets:[{data:[j.risk,100-j.risk]}]}
 });
}

async function load(){
 let r=await fetch("/api/news");
 let j=await r.json();

 let f = document.getElementById("filter").value;
 document.getElementById("fval").innerText=f;

 t.innerText=j.stats.total;
 d.innerText=j.stats.danger;
 s.innerText=j.stats.safe;

 let html="";
 let risks=[];

 j.data.forEach(n=>{
  if(n.risk>=f){
    html+=`<p>${n.text}<br><span class="${color(n.risk)}">${n.risk}%</span></p>`;
    risks.push(n.risk);
  }
 });

 news.innerHTML=html;

 if(bar) bar.destroy();

 bar=new Chart(document.getElementById("bar"),{
  type:"bar",
  data:{
    labels: risks.map((_,i)=>"H"+i),
    datasets:[{label:"Risk",data:risks}]
  }
 });
}

setInterval(load,4000);
load();
</script>

</body>
</html>
""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)