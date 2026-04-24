from flask import Flask, request, jsonify, render_template_string
import requests, smtplib, os, hashlib, time
import xml.etree.ElementTree as ET

app = Flask(__name__)

cache = []
stats = {"total": 0, "high": 0, "safe": 0}
sent = set()
last = 0

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
        return [i.find("title").text for i in root.findall(".//item")[:15]]
    except:
        return []

# ---------------- SOSYAL MEDYA BENZERİ ----------------
def google_search_sim():
    # Google arama simülasyonu (yasal yaklaşım)
    return [
        "site:x.com şok iddia hızla yayılıyor",
        "site:instagram.com inanılmaz olay sosyal medyada",
        "site:tiktok.com gizli gerçek ortaya çıktı",
    ]

def trends():
    try:
        r = requests.get("https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR").text
        items = r.split("<title>")[1:10]
        return [i.split("</title>")[0] for i in items]
    except:
        return []

# ---------------- KAYNAKLAR ----------------
def get_news():
    data = []

    data += parse("https://teyit.org/feed")
    data += parse("https://www.dogrulukpayi.com/rss.xml")
    data += parse("https://malumatfurus.org/feed")
    data += parse("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr")

    data += trends()
    data += google_search_sim()

    if len(data) < 5:
        data += [
            "ŞOK HABER herkes paylaşıyor",
            "Gizli bilgi ortaya çıktı",
            "İnanılmaz olay yayılıyor"
        ]

    return data

# ---------------- RISK ----------------
def risk(text):
    s = 30
    t = text.lower()

    keys = ["şok","acil","gizli","ifşa","iddia","herkes","yayılıyor"]

    for k in keys:
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

    data = []
    total = 0
    high = 0
    safe = 0

    for n in get_news():
        r = risk(n)
        total += 1

        if r >= 50:
            data.append({"title": n, "risk": r})

        if r >= 80:
            high += 1
            h = hashlib.md5(n.encode()).hexdigest()
            if h not in sent:
                send_email(n, r)
                sent.add(h)
        else:
            safe += 1

    cache = data[:15]
    stats = {"total": total, "high": high, "safe": safe}

# ---------------- API ----------------
@app.route("/api/news")
def news():
    refresh()
    return {"data": cache, "stats": stats}

@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text")
    r = risk(text)

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
body{
 background:#020617;
 color:white;
 font-family:Arial;
 padding:20px;
}
h1{
 text-align:center;
 font-size:40px;
}
.container{
 max-width:1000px;
 margin:auto;
}
.stats{
 display:flex;
 gap:15px;
 justify-content:center;
}
.box{
 background:#0f172a;
 padding:20px;
 border-radius:15px;
 width:150px;
 text-align:center;
}
.card{
 background:#0f172a;
 padding:15px;
 margin-top:15px;
 border-radius:15px;
}
input{
 width:100%;
 padding:10px;
 border-radius:10px;
 border:none;
}
button{
 margin-top:10px;
 padding:10px;
 width:100%;
 border:none;
 background:#2563eb;
 color:white;
 border-radius:10px;
}
.high{color:red;}
.mid{color:orange;}
.low{color:lightgreen;}
canvas{
 max-width:250px;
 margin:auto;
 display:block;
}
</style>
</head>

<body>

<div class="container">

<h1>Dezenformasyona Karşı Yapay Zeka</h1>

<div class="stats">
<div class="box">Toplam<br><b id="t">0</b></div>
<div class="box">Riskli<br><b id="h">0</b></div>
<div class="box">Güvenli<br><b id="s">0</b></div>
</div>

<div class="card">
<input id="txt" placeholder="Metin gir">
<button onclick="analyze()">Analiz</button>
<h3 id="res"></h3>
<canvas id="chart"></canvas>
</div>

<div class="card">
<h2>Son Analizler</h2>
<div id="news"></div>
</div>

</div>

<script>
let chart;

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

 if(chart) chart.destroy();

 chart=new Chart(chart=document.getElementById("chart"),{
  type:"doughnut",
  data:{labels:["Risk","Safe"],datasets:[{data:[j.risk,100-j.risk]}]}
 });
}

async function load(){
 let r=await fetch("/api/news");
 let j=await r.json();

 t.innerText=j.stats.total;
 h.innerText=j.stats.high;
 s.innerText=j.stats.safe;

 let html="";
 j.data.forEach(n=>{
  html+=`<p>${n.title}<br><span class="${color(n.risk)}">${n.risk}%</span></p>`;
 });

 news.innerHTML=html;
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