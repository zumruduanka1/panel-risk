from flask import Flask, request, jsonify, render_template_string
import requests, smtplib, os, time, hashlib, random
import xml.etree.ElementTree as ET

app = Flask(__name__)

cache = []
stats = {"total": 0, "risk": 0, "safe": 0}
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

        msg = f"Subject: 🚨 Yüksek Riskli İçerik\n\n{text}\nRisk: {risk}%"
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

# ---------------- SOSYAL VERİ ----------------
def social_data():
    base = [
        "ŞOK! herkes bunu konuşuyor",
        "gizli gerçek ortaya çıktı",
        "inanılmaz video yayıldı",
        "büyük skandal iddiası",
        "herkes bu haberi paylaşıyor",
        "ifşa edilen görüntüler olay oldu",
        "uzmanlar uyardı deniliyor",
        "viral video tartışma yarattı",
        "sosyal medyada korkutan iddia",
        "kanıtlandığı iddia edilen olay"
    ]
    return [random.choice(base) for _ in range(25)]

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
    data += social_data()
    return data

# ---------------- RISK ENGINE ----------------
def url_risk(text):
    risk = 0
    if "http" in text:
        if any(x in text for x in [".xyz",".click",".info",".news"]):
            risk += 30
        if "-" in text or len(text) > 80:
            risk += 10
    return risk

def media_risk(text):
    t = text.lower()
    if any(x in t for x in ["video","görüntü","fotoğraf","kanıt","izle"]):
        return 15
    return 0

def viral_risk(text):
    t = text.lower()
    risk = 0
    if "herkes" in t:
        risk += 10
    if text.count("!") >= 2:
        risk += 15
    return risk

def risk_score(text):
    s = 30
    t = text.lower()

    keywords = ["şok","gizli","ifşa","iddia","herkes","yayılıyor","inanılmaz"]

    for k in keywords:
        if k in t:
            s += 15

    if "!" in text:
        s += 10

    if len(text) < 40:
        s += 10

    s += url_risk(text)
    s += media_risk(text)
    s += viral_risk(text)

    return min(s, 100)

# ---------------- REFRESH ----------------
def refresh():
    global cache, stats, last

    if time.time() - last < 20:
        return

    last = time.time()

    raw = collect()

    out = []
    total = 0
    risk_count = 0
    safe = 0

    for item in raw:
        r = risk_score(item)
        total += 1

        if r >= 50:
            out.append({"text": item, "risk": r})
            risk_count += 1
        else:
            safe += 1

        if r >= 80:
            h = hashlib.md5(item.encode()).hexdigest()
            if h not in sent:
                send_email(item, r)
                sent.add(h)

    cache = out[:30]
    stats = {"total": total, "risk": risk_count, "safe": safe}

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
<style>
body{background:#020617;color:white;font-family:Arial;padding:20px;}
.container{max-width:1000px;margin:auto;}
.title{text-align:center;font-size:40px;font-weight:bold;}
.subtitle{text-align:center;color:#94a3b8;margin-bottom:30px;}
.stats{display:flex;justify-content:center;gap:20px;margin-bottom:20px;}
.box{background:#0f172a;padding:20px;border-radius:12px;width:150px;text-align:center;}
.card{background:#0f172a;padding:20px;border-radius:12px;margin-top:20px;}
input{width:100%;padding:10px;border-radius:10px;border:none;}
button{margin-top:10px;padding:10px;width:100%;background:#2563eb;border:none;border-radius:10px;color:white;}
.high{color:#ef4444;} .mid{color:#facc15;} .low{color:#22c55e;}
</style>
</head>

<body>

<div class="container">

<div class="title">Dezenformasyona Karşı Yapay Zeka</div>
<div class="subtitle">Sosyal medya içeriklerini analiz eder ve risk puanı üretir</div>

<div class="stats">
<div class="box">Toplam<br><b id="t">0</b></div>
<div class="box">Riskli<br><b id="r">0</b></div>
<div class="box">Güvenli<br><b id="s">0</b></div>
</div>

<div class="card">
<h3>Metin Analizi</h3>
<input id="txt" placeholder="Haber gir...">
<button onclick="analyze()">Analiz Et</button>
<h3 id="res"></h3>
</div>

<div class="card">
<h3>Yüksek Riskli İçerikler (≥50)</h3>
<div id="news"></div>
</div>

</div>

<script>
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
}

async function load(){
 let r=await fetch("/api/news");
 let j=await r.json();

 t.innerText=j.stats.total;
 r.innerText=j.stats.risk;
 s.innerText=j.stats.safe;

 let html="";
 j.data.forEach(n=>{
  html+=`<p>${n.text}<br><span class="${color(n.risk)}">${n.risk}%</span></p>`;
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