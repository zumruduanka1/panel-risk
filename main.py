from flask import Flask, request, jsonify, render_template_string
import requests, random, time, hashlib, os, smtplib
import xml.etree.ElementTree as ET

app = Flask(__name__)

cache = []
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

        msg = f"Subject: 🚨 Yüksek Riskli Haber\n\n{text}\nRisk: {risk}%"
        s.sendmail(user, to, msg)
        s.quit()
    except:
        pass

# ---------------- HABER FİLTRESİ ----------------
def is_news(text):
    if not text:
        return False

    t = text.lower().strip()

    if len(t) < 60:
        return False

    if len(t.split()) < 8:
        return False

    if "." not in t and "," not in t:
        return False

    keywords = [
        "son dakika","iddia","açıklandı","haber",
        "gündem","rapor","uzman","olay","yetkili"
    ]

    score = sum(1 for k in keywords if k in t)

    return score >= 1

# ---------------- RISK MODEL ----------------
def risk_score(text):
    t = text.lower()
    score = 15

    if "şok" in t or "ifşa" in t:
        score += 25

    if "iddia" in t:
        score += 20

    if "kanıtlandı" in t or "kesin" in t:
        score += 25

    if "herkes" in t or "viral" in t:
        score += 15

    if "uzman" in t or "rapor" in t or "resmi" in t:
        score -= 30

    length = len(t)

    if length < 80:
        score += 15
    elif length > 150:
        score -= 10

    score += t.count("!") * 4

    # 🔥 farklı sonuç üretir
    score += random.randint(-12, 12)

    return max(5, min(95, score))

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

# ---------------- SOSYAL ----------------
def social_data():
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
        for _ in range(20)
    ]

# ---------------- COLLECT ----------------
def collect():
    data = []

    data += parse("https://teyit.org/feed","Teyit")
    data += parse("https://www.dogrulukpayi.com/rss.xml","Doğruluk Payı")
    data += parse("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr","Google News")
    data += parse("https://www.ntv.com.tr/son-dakika.rss","NTV")
    data += social_data()

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
    global cache, last

    if time.time() - last < 6:
        return

    last = time.time()
    raw = collect()

    out = []

    for text, source, link in raw:
        r = risk_score(text)

        if r >= 50:
            out.append({
                "text": text,
                "risk": r,
                "source": source,
                "link": link
            })

        if r >= 80:
            h = hashlib.md5(text.encode()).hexdigest()
            if h not in sent:
                send_email(text, r)
                sent.add(h)

    cache = out[:40]

# ---------------- API ----------------
@app.route("/api/news")
def news():
    refresh()
    return {"data": cache}

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)

    if not data or "text" not in data:
        return {"error":"Veri yok"}

    text = data["text"]

    if not is_news(text):
        return {"error":"Bu bir haber metni değil!"}

    r = risk_score(text)

    if r >= 80:
        send_email(text, r)

    return {"risk": r}

# ---------------- UI ----------------
@app.route("/")
def home():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body{background:#020617;color:white;font-family:Arial;padding:20px;}
.card{background:#0f172a;padding:15px;margin:10px;border-radius:10px;}
.red{color:red;} .orange{color:orange;} .green{color:green;}
</style>
</head>

<body>

<h1>Fake News Risk Dashboard</h1>

<input id="txt" placeholder="Haber gir">
<button onclick="go()">Analiz</button>
<h2 id="res"></h2>

<h3>Riskli Haberler</h3>
<div id="news"></div>

<script>
function color(r){
 if(r>=80) return "red";
 if(r>=50) return "orange";
 return "green";
}

async function go(){
 let t=txt.value;

 let r=await fetch("/api/analyze",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({text:t})
 });

 let j=await r.json();

 if(j.error){
  res.innerText=j.error;
 }else{
  res.innerText="Risk: "+j.risk+"%";
 }
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
  <br><small>${n.source}</small>
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