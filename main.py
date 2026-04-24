from flask import Flask, request, jsonify, render_template_string
import requests, random, time, hashlib, os, smtplib
import xml.etree.ElementTree as ET

app = Flask(__name__)

cache = []
sent = set()
last = 0

stats = {"total":0,"risk":0,"avg":0}

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

        msg = f"Subject: 🚨 Yüksek Riskli Haber\n\n{text}\nRisk: {risk}%"
        s.sendmail(user, to, msg)
        s.quit()
    except:
        pass

# ---------------- HABER KONTROL ----------------
def is_news(text):
    if not text or len(text) < 40:
        return False

    keywords = [
        "son dakika","iddia","açıklandı","haber",
        "görüntü","rapor","uzman","gündem","olay"
    ]

    score = sum(1 for k in keywords if k in text.lower())

    if len(text.split()) < 6:
        return False

    return score >= 1

# ---------------- ANALİZ ----------------
def explain(text):
    t = text.lower()
    reasons = []

    if "şok" in t:
        reasons.append("abartılı dil")

    if "iddia" in t:
        reasons.append("doğrulanmamış bilgi")

    if "gizli" in t:
        reasons.append("manipülasyon")

    if "herkes" in t:
        reasons.append("viral yayılım")

    if "kanıtlandı" in t:
        reasons.append("kesinlik iddiası")

    if "uzman" in t:
        reasons.append("uzman görüşü (daha güvenli)")

    return reasons if reasons else ["nötr içerik"]

def risk(text):
    t = text.lower()
    score = 0

    # clickbait
    for k in ["şok","inanılmaz","korkutan","ifşa","gizli"]:
        if k in t:
            score += 15

    # kesinlik
    if "kanıtlandı" in t or "kesin" in t:
        score += 30

    # iddia
    if "iddia" in t:
        score += 20

    # viral
    if "herkes" in t or "viral" in t:
        score += 15

    # güven düşür
    if "uzman" in t or "resmi" in t or "rapor" in t:
        score -= 25

    # uzunluk
    if len(text) < 50:
        score += 20
    elif len(text) > 120:
        score -= 10

    # ünlem
    score += text.count("!") * 5

    score = max(score, 5)
    return min(100, score)

# ---------------- RSS ----------------
def parse(url, source):
    data = []
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)

        for i in root.findall(".//item")[:15]:
            data.append((
                i.find("title").text,
                source,
                i.find("link").text
            ))
    except:
        pass
    return data

# ---------------- SOSYAL ----------------
def social_real():
    konular = ["deprem","aşı","seçim","ekonomi","savaş","teknoloji"]
    duygular = ["şok","gizli","ifşa","inanılmaz"]

    templates = [
        "SON DAKİKA: {k} hakkında {d} iddia!",
        "{k} ile ilgili {d} görüntüler ortaya çıktı",
        "{k} sosyal medyada viral oldu",
        "{k} hakkında herkes bunu konuşuyor"
    ]

    return [
        (random.choice(templates).format(
            k=random.choice(konular),
            d=random.choice(duygular)
        ), "Sosyal Medya", "#")
        for _ in range(30)
    ]

# ---------------- COLLECT ----------------
def collect():
    data = []

    data += parse("https://teyit.org/feed","Teyit")
    data += parse("https://www.dogrulukpayi.com/rss.xml","Doğruluk")
    data += parse("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr","Google News")
    data += parse("https://www.bbc.com/turkce/index.xml","BBC")
    data += parse("https://www.ntv.com.tr/son-dakika.rss","NTV")
    data += social_real()

    seen = set()
    unique = []

    for d in data:
        key = d[0].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(d)

    random.shuffle(unique)
    return unique

# ---------------- REFRESH ----------------
def refresh():
    global cache, last, stats

    if time.time() - last < 5:
        return

    last = time.time()
    raw = collect()

    out = []
    total = 0
    risk_c = 0
    avg = 0

    for text, source, link in raw:
        r = risk(text)

        if explain(text) == ["nötr içerik"]:
            r = max(5, r - 25)

        total += 1
        avg += r

        if r >= 50:
            out.append({
                "text": text,
                "risk": r,
                "source": source,
                "link": link,
                "reasons": explain(text)
            })
            risk_c += 1

        if r >= 80:
            h = hashlib.md5(text.encode()).hexdigest()
            if h not in sent:
                send_email(text, r)
                sent.add(h)

    cache = out[:50]

    stats = {
        "total": total,
        "risk": risk_c,
        "avg": int(avg / total) if total else 0
    }

# ---------------- API ----------------
@app.route("/api/news")
def news():
    refresh()
    return {"data": cache, "stats": stats}

@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text")

    if not is_news(text):
        return {"error": "Lütfen haber formatında bir içerik girin!"}

    r = risk(text)

    if explain(text) == ["nötr içerik"]:
        r = max(5, r - 25)

    if r >= 80:
        send_email(text, r)

    return {"risk": r, "reasons": explain(text)}

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
.card{background:#0f172a;padding:15px;border-radius:10px;margin:10px;}
.high{color:red;} .mid{color:orange;} .low{color:green;}
</style>
</head>

<body>

<div class="container">

<h1>ULTRA REAL Fake News Dashboard</h1>

<div class="card">
<input id="txt" placeholder="Haber gir">
<button onclick="analyze()">Analiz</button>
<h3 id="res"></h3>
<canvas id="chart"></canvas>
</div>

<div class="card">
<h3>İstatistik</h3>
<p id="stats"></p>
</div>

<div class="card">
<h3>Akış</h3>
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
 let t=txt.value;

 let r=await fetch("/api/analyze",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({text:t})
 });

 let j=await r.json();

 if(j.error){
  res.innerHTML=j.error;
  return;
 }

 res.innerHTML=j.risk+"% ("+j.reasons.join(", ")+")";

 if(chart) chart.destroy();

 chart=new Chart(document.getElementById("chart"),{
  type:"bar",
  data:{labels:["Risk"],datasets:[{data:[j.risk]}]}
 });
}

async function load(){
 let r=await fetch("/api/news");
 let j=await r.json();

 stats.innerHTML="Toplam: "+j.stats.total+" | Riskli: "+j.stats.risk+" | Ortalama: "+j.stats.avg;

 let html="";
 j.data.forEach(n=>{
  html+=`
  <div class="card">
  <a href="${n.link}" target="_blank">${n.text}</a><br>
  <span class="${color(n.risk)}">${n.risk}%</span>
  <br><small>${n.source}</small>
  <br><small>${n.reasons.join(", ")}</small>
  </div>`;
 });

 news.innerHTML=html;
}

setInterval(load,5000);
load();
</script>

</body>
</html>
""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)