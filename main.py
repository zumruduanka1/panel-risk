from flask import Flask, request, jsonify, render_template_string
import requests, random, time, hashlib, os, smtplib
import xml.etree.ElementTree as ET

app = Flask(__name__)

cache = []
stats = {"total":0,"risk":0,"safe":0}
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

# ---------------- NEWS CHECK ----------------
def is_news(text):
    if not text or len(text)<20:
        return False

    keys=["iddia","son dakika","açıklandı","haber","video","görüntü"]
    return any(k in text.lower() for k in keys) or len(text.split())>6

# ---------------- AI ----------------
def explain(text):
    t=text.lower()
    r=[]

    if "şok" in t: r.append("clickbait")
    if "gizli" in t: r.append("manipülasyon")
    if "herkes" in t: r.append("viral yayılım")
    if "iddia" in t: r.append("doğrulanmamış")

    return r

def risk(text):
    t=text.lower()
    s=20

    for k in ["şok","ifşa","gizli","kanıtlandı"]:
        if k in t: s+=20

    for k in ["iddia","viral","herkes","paylaşılıyor"]:
        if k in t: s+=10

    if "!" in text: s+=10
    if len(text)<30: s+=10

    return min(100,s)

# ---------------- RSS ----------------
def parse(url, source):
    data=[]
    try:
        r=requests.get(url,timeout=5)
        root=ET.fromstring(r.content)

        for i in root.findall(".//item")[:10]:
            data.append((i.find("title").text,source,i.find("link").text))
    except:
        pass
    return data

# ---------------- SOCIAL ----------------
def social():
    konular=["deprem","aşı","seçim","ekonomi","savaş","teknoloji"]
    duygular=["şok","gizli","ifşa","inanılmaz","korkutan"]

    templates=[
        "SON DAKİKA: {k} hakkında {d} iddia!",
        "{k} ile ilgili {d} görüntüler ortaya çıktı",
        "{k} sosyal medyada viral oldu",
        "{k} hakkında herkes bunu konuşuyor",
        "Uzmanlar uyardı: {k} tehlikeli olabilir",
    ]

    return [(random.choice(templates).format(k=random.choice(konular),d=random.choice(duygular)),"Sosyal","#") for _ in range(40)]

# ---------------- COLLECT ----------------
def collect():
    data=[]
    data+=parse("https://teyit.org/feed","Teyit")
    data+=parse("https://www.dogrulukpayi.com/rss.xml","Doğruluk")
    data+=parse("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr","Google News")
    data+=social()

    seen=set()
    unique=[]

    for d in data:
        if d[0] not in seen:
            seen.add(d[0])
            unique.append(d)

    return unique

# ---------------- REFRESH ----------------
def refresh():
    global cache, stats, last

    if time.time()-last<5:
        return

    last=time.time()
    raw=collect()

    out=[]
    total=0
    risk_c=0
    safe=0

    for text,source,link in raw:
        r=risk(text)
        total+=1

        if r>=50:
            out.append({
                "text":text,
                "risk":r,
                "source":source,
                "link":link,
                "reasons":explain(text)
            })
            risk_c+=1
        else:
            safe+=1

        if r>=80:
            h=hashlib.md5(text.encode()).hexdigest()
            if h not in sent:
                send_email(text,r)
                sent.add(h)

    cache=out[:40]
    stats={"total":total,"risk":risk_c,"safe":safe}

# ---------------- API ----------------
@app.route("/api/news")
def news():
    refresh()
    return {"data":cache,"stats":stats}

@app.route("/api/analyze",methods=["POST"])
def analyze():
    text=request.json.get("text")

    if not is_news(text):
        return {"error":"Sadece haber içerikleri analiz edilir!"}

    r=risk(text)
    reasons=explain(text)

    if r>=80:
        send_email(text,r)

    return {"risk":r,"reasons":reasons}

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

<h1>AI Fake News Dashboard</h1>

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
<h3>En Riskli Haberler</h3>
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
  type:"doughnut",
  data:{labels:["Risk","Safe"],datasets:[{data:[j.risk,100-j.risk]}]}
 });
}

async function load(){
 let r=await fetch("/api/news");
 let j=await r.json();

 stats.innerHTML="Toplam: "+j.stats.total+" | Riskli: "+j.stats.risk;

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

setInterval(load,4000);
load();
</script>

</body>
</html>
""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)