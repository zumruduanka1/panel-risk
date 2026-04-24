from flask import Flask, request, jsonify, render_template_string
import sqlite3, requests, time, hashlib, random, os, smtplib
import xml.etree.ElementTree as ET

# AI MODEL (light)
try:
    from transformers import pipeline
    classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")
except:
    classifier = None

app = Flask(__name__)

# ---------------- DATABASE ----------------
def db():
    conn = sqlite3.connect("data.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS news(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        risk INTEGER,
        source TEXT,
        link TEXT
    )
    """)
    return conn

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

# ---------------- FILTER ----------------
def is_news(text):
    if not text or len(text) < 20:
        return False

    keys = ["iddia","son dakika","açıklandı","haber","video"]
    return any(k in text.lower() for k in keys) or len(text.split()) > 6

# ---------------- AI RISK ----------------
def ai_score(text):
    if classifier:
        try:
            res = classifier(text[:200])[0]
            if res["label"] == "NEGATIVE":
                return min(90, int(res["score"] * 100))
            else:
                return int((1 - res["score"]) * 50)
        except:
            pass

    # fallback
    s = 30
    if "şok" in text.lower(): s += 20
    if "gizli" in text.lower(): s += 15
    if "!" in text: s += 10
    return min(s, 100)

# ---------------- DATA ----------------
def parse(url, source):
    data = []
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)
        for i in root.findall(".//item")[:10]:
            data.append((i.find("title").text, source, i.find("link").text))
    except:
        pass
    return data

def social():
    t = [
        "SON DAKİKA: deprem hakkında şok iddia!",
        "aşı ile ilgili gizli gerçek ortaya çıktı",
        "herkes bunu konuşuyor dikkat edin"
    ]
    return [(random.choice(t),"Sosyal","#") for _ in range(30)]

def collect():
    data = []
    data += parse("https://teyit.org/feed","Teyit")
    data += parse("https://www.dogrulukpayi.com/rss.xml","Doğruluk")
    data += parse("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr","Google")
    data += social()

    seen = set()
    unique = []

    for d in data:
        if d[0] not in seen:
            seen.add(d[0])
            unique.append(d)

    return unique

# ---------------- REFRESH ----------------
def refresh():
    data = collect()
    conn = db()

    for text, source, link in data:
        r = ai_score(text)

        conn.execute(
            "INSERT INTO news(text,risk,source,link) VALUES(?,?,?,?)",
            (text, r, source, link)
        )

        if r >= 80:
            send_email(text, r)

    conn.commit()
    conn.close()

# ---------------- API ----------------
@app.route("/api/news")
def news():
    refresh()

    conn = db()
    rows = conn.execute("SELECT text,risk,source,link FROM news ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()

    return {"data":[{"text":r[0],"risk":r[1],"source":r[2],"link":r[3]} for r in rows]}

@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text")

    if not is_news(text):
        return {"error":"Sadece haber içerikleri analiz edilir!"}

    r = ai_score(text)

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
.card{background:#0f172a;padding:15px;border-radius:10px;margin:10px;}
.high{color:red;} .mid{color:orange;} .low{color:green;}
</style>
</head>

<body>

<h1>ULTRA AI Fake News</h1>

<input id="txt">
<button onclick="analyze()">Analiz</button>
<h3 id="res"></h3>
<canvas id="chart"></canvas>

<div id="news"></div>

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
  res.innerHTML=j.error;
  return;
 }

 res.innerHTML=j.risk+"%";

 if(chart) chart.destroy();

 chart=new Chart(document.getElementById("chart"),{
  type:"doughnut",
  data:{labels:["Risk","Safe"],datasets:[{data:[j.risk,100-j.risk]}]}
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
  <span class="${color(n.risk)}">${n.risk}%</span>
  <br>${n.source}
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