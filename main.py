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

        msg = f"Subject: 🚨 Yüksek Risk\n\n{text}\nRisk: {risk}%"
        s.sendmail(user, to, msg)
        s.quit()
    except:
        pass

# ---------------- HABER KONTROL ----------------
def is_news_like(text):
    if not text or len(text.strip()) < 15:
        return False

    keywords = ["iddia","son dakika","açıklandı","oldu","paylaşıldı"]

    if any(k in text.lower() for k in keywords):
        return True

    if len(text.split()) > 5:
        return True

    return False

# ---------------- RSS ----------------
def parse(url, source):
    data = []
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)

        for i in root.findall(".//item")[:10]:
            title = i.find("title").text
            link = i.find("link").text
            data.append((title, source, link))
    except:
        pass
    return data

# ---------------- SOSYAL VERİ ----------------
def social_data():
    konular = ["deprem","aşı","seçim","ekonomi","savaş","teknoloji"]
    duygular = ["şok","gizli","ifşa","inanılmaz","korkutan"]

    templates = [
        "SON DAKİKA: {konu} hakkında {duygu} iddia!",
        "{konu} ile ilgili {duygu} görüntüler ortaya çıktı",
        "{konu} sosyal medyada viral oldu",
        "Uzmanlar uyardı: {konu} tehlikeli olabilir",
    ]

    return [(random.choice(templates).format(konu=random.choice(konular),duygu=random.choice(duygular)),"Sosyal Medya","#") for _ in range(40)]

def human_style():
    samples = [
        "arkadaşlar bu doğru mu?",
        "herkes paylaşıyor dikkat edin",
        "çok garip ama gerçek gibi duruyor",
        "bunu kimse konuşmuyor ama önemli"
    ]
    return [(random.choice(samples),"Kullanıcı","#") for _ in range(10)]

def collect():
    data = []
    data += parse("https://teyit.org/feed","Teyit")
    data += parse("https://www.dogrulukpayi.com/rss.xml","Doğruluk Payı")
    data += parse("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr","Google News")
    data += social_data()
    data += human_style()
    return data

# ---------------- RISK ----------------
def explain(text):
    t = text.lower()
    reasons = []

    if "şok" in t: reasons.append("clickbait")
    if "gizli" in t: reasons.append("manipülasyon")
    if "video" in t: reasons.append("kanıtsız medya")
    if "herkes" in t: reasons.append("viral yayılım")

    return reasons

def risk_score(text):
    t = text.lower()
    s = 20

    strong = ["şok","ifşa","gizli","kanıtlandı"]
    medium = ["iddia","viral","herkes","paylaşıyor"]

    for k in strong:
        if k in t:
            s += 20

    for k in medium:
        if k in t:
            s += 10

    if "!" in text:
        s += 10

    if len(text) < 30:
        s += 10

    if len(text) > 120:
        s -= 10

    return max(0, min(s, 100))

# ---------------- REFRESH ----------------
def refresh():
    global cache, stats, last

    if time.time() - last < 5:
        return

    last = time.time()
    raw = collect()

    out = []
    total = 0
    risk_count = 0
    safe = 0

    for item in raw:
        text, source, link = item
        r = risk_score(text)
        total += 1

        if r >= 50:
            out.append({
                "text": text,
                "risk": r,
                "source": source,
                "link": link
            })
            risk_count += 1
        else:
            safe += 1

        if r >= 80:
            h = hashlib.md5(text.encode()).hexdigest()
            if h not in sent:
                send_email(text, r)
                sent.add(h)

    cache = out[:40]
    stats = {"total": total, "risk": risk_count, "safe": safe}

# ---------------- API ----------------
@app.route("/api/news")
def news():
    refresh()
    return {"data": cache, "stats": stats}

@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text")

    if not is_news_like(text):
        return {"error": "Bu bir haber metni gibi görünmüyor!"}

    r = risk_score(text)
    reasons = explain(text)

    if r >= 80:
        send_email(text, r)

    return {"risk": r, "reasons": reasons}

# ---------------- UI ----------------
@app.route("/")
def home():
    return render_template_string("""
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#020617;color:white;font-family:Arial;padding:20px;}
.container{max-width:1000px;margin:auto;}
.title{text-align:center;font-size:40px;}
.card{background:#0f172a;padding:20px;border-radius:12px;margin-top:20px;}
input{width:100%;padding:10px;border-radius:10px;border:none;}
button{margin-top:10px;padding:10px;width:100%;background:#2563eb;border:none;color:white;border-radius:10px;}
.high{color:red;} .mid{color:orange;} .low{color:green;}
a{color:white;text-decoration:none;}
</style>
</head>

<body>

<div class="container">

<div class="title">AI Fake News Detector</div>

<div class="card">
<input id="txt" placeholder="Metin gir">
<button onclick="analyze()">Analiz</button>
<h3 id="res"></h3>
<canvas id="chart"></canvas>
</div>

<div class="card">
<h3>Riskli İçerikler</h3>
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

 if(j.error){
  res.innerHTML="<span style='color:red'>"+j.error+"</span>";
  return;
 }

 res.innerHTML=j.risk+"% ("+j.reasons.join(", ")+")";

 if(chart) chart.destroy();

 chart=new Chart(document.getElementById("chart"),{
  type:"doughnut",
  data:{
    labels:["Risk","Safe"],
    datasets:[{data:[j.risk,100-j.risk]}]
  }
 });
}

async function load(){
 let r=await fetch("/api/news");
 let j=await r.json();

 let html="";
 j.data.forEach(n=>{
  html+=`
  <div class="card">
  <a href="${n.link}" target="_blank">${n.text}</a><br>
  <span class="${color(n.risk)}">${n.risk}%</span><br>
  <small>${n.source}</small>
  </div>`;
 });

 news.innerHTML=html;
}

setInterval(load,3000);
load();
</script>

</body>
</html>
""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)