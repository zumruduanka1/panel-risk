from flask import Flask, request, jsonify, render_template_string, redirect, session
import sqlite3, os, hashlib, requests, smtplib, time, random
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

app = Flask(__name__)
app.secret_key = "defans_secret"

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, username TEXT, text TEXT, risk INTEGER)")

    conn.commit()
    conn.close()

init_db()

# ---------------- EMAIL ----------------
def send_email(text, risk):
    try:
        user = os.getenv("tubitaktest0@gmail.com")
        pw = os.getenv("umdyxtmpeljhodhy")
        to = os.getenv("rumeyysauslu@gmail.com")

        if not user:
            return

        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(user, pw)

        msg = f"Subject: 🚨 DEFANS ALERT\n\n{text}\nRisk: {risk}%"
        s.sendmail(user, to, msg)
        s.quit()
    except:
        pass

# ---------------- AI ----------------
def ai_score(text):
    try:
        headers = {"Authorization": f"Bearer {os.getenv('HF_API_KEY')}"}

        payload = {
            "inputs": text,
            "parameters": {
                "candidate_labels": ["fake news","true news"]
            }
        }

        r = requests.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-mnli",
            headers=headers,
            json=payload,
            timeout=8
        )

        data = r.json()

        if isinstance(data, list):
            scores = dict(zip(data[0]["labels"], data[0]["scores"]))
            return int(scores.get("fake news", 0) * 100)

    except:
        return None

# ---------------- BASE ----------------
def base_score(text):
    t = text.lower()
    score = 30

    if "şok" in t or "ifşa" in t:
        score += 20
    if "iddia" in t:
        score += 15
    if "kanıtlandı" in t:
        score += 20
    if "uzman" in t or "rapor" in t:
        score -= 25

    return max(5, min(95, score))

def risk_score(text):
    ai = ai_score(text)
    base = base_score(text)

    if ai is not None:
        return int(ai * 0.6 + base * 0.4)
    return base

# ---------------- FILTER ----------------
def is_news(text):
    t = text.lower()
    return len(t) > 50 and any(k in t for k in ["haber","iddia","son dakika","gündem"])

# ---------------- URL ----------------
def extract_url(url):
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.title.string.strip()
    except:
        return None

# ---------------- IMAGE ----------------
def extract_img(url):
    try:
        name = urlparse(url).path.split("/")[-1]
        return name.replace("-", " ").replace("_", " ")
    except:
        return None

# ---------------- RSS ----------------
def parse_rss(url, source):
    data = []
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)

        for i in root.findall(".//item")[:8]:
            title = i.find("title").text
            link = i.find("link").text
            data.append((title, source, link))
    except:
        pass
    return data

def social_feed():
    topics = ["deprem","aşı","seçim","ekonomi","savaş"]
    words = ["şok","ifşa","gizli"]

    return [(f"{random.choice(topics)} hakkında {random.choice(words)} iddia","Sosyal Medya","#") for _ in range(10)]

# ---------------- CACHE ----------------
cache = []
last = 0

def refresh():
    global cache, last

    if time.time() - last < 10:
        return

    last = time.time()

    data = []
    data += parse_rss("https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr","Google")
    data += parse_rss("https://www.ntv.com.tr/son-dakika.rss","NTV")
    data += parse_rss("https://www.bbc.com/turkce/index.xml","BBC")
    data += parse_rss("https://teyit.org/feed","Teyit")
    data += social_feed()

    out = []

    for text, source, link in data:
        r = risk_score(text)

        if r >= 50:
            out.append({"text":text,"risk":r,"source":source,"link":link})

        if r >= 80:
            send_email(text, r)

    cache = out[:30]

# ---------------- AUTH ----------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        u = request.form["u"]
        p = hashlib.md5(request.form["p"].encode()).hexdigest()

        conn = sqlite3.connect("data.db")
        conn.execute("INSERT INTO users(username,password) VALUES(?,?)",(u,p))
        conn.commit()
        conn.close()

        return redirect("/login")

    return "<form method=post><input name=u><input name=p><button>Kayıt</button></form>"

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = hashlib.md5(request.form["p"].encode()).hexdigest()

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = u
            return redirect("/")

    return "<form method=post><input name=u><input name=p><button>Giriş</button></form>"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- API ----------------
@app.route("/api/news")
def news():
    refresh()
    return {"data": cache}

@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "user" not in session:
        return {"error":"login gerekli"}

    text = request.json.get("text")

    if text.startswith("http"):
        if text.endswith((".jpg",".png",".jpeg",".webp")):
            text = extract_img(text)
        else:
            text = extract_url(text)

    if not text or not is_news(text):
        return {"error":"Bu bir haber değil"}

    r = risk_score(text)

    conn = sqlite3.connect("data.db")
    conn.execute("INSERT INTO history(username,text,risk) VALUES(?,?,?)",(session["user"],text,r))
    conn.commit()
    conn.close()

    if r >= 80:
        send_email(text, r)

    return {"risk":r,"text":text}

# ---------------- UI ----------------
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("data.db")
    data = conn.execute("SELECT text,risk FROM history WHERE username=? ORDER BY id DESC LIMIT 10",(session["user"],)).fetchall()
    conn.close()

    items = "".join([f"<li>{t} - %{r}</li>" for t,r in data])

    return f"""
    <html>
    <head><title>DEFANS</title></head>
    <body style="background:black;color:white;font-family:Arial">

    <h1>DEFANS - Fake News Shield</h1>

    <a href='/logout'>Çıkış</a><br><br>

    <input id='txt'>
    <button onclick='go()'>Analiz</button>

    <h2 id='res'></h2>

    <h3>Geçmiş</h3>
    <ul>{items}</ul>

<script>
async function go(){{
 let t=document.getElementById("txt").value;
 let r=await fetch("/api/analyze",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{text:t}})}});
 let j=await r.json();
 if(j.error) res.innerText=j.error;
 else res.innerText="Risk: "+j.risk+"%";
}}
</script>

</body>
</html>
"""

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)