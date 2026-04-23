from flask import Flask, jsonify, request, render_template_string
import requests
import difflib
import smtplib

app = Flask(__name__)

data = {"news": []}

# ---------------- FAKE SCORE ----------------
def fake_score(text):
    score = 0
    text = text.lower()

    keywords = ["şok", "son dakika", "inanılmaz", "öldü", "ifşa", "gizli"]

    for k in keywords:
        if k in text:
            score += 15

    if text.isupper():
        score += 20

    return min(score, 100)

# ---------------- SIMILARITY ----------------
def similarity(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

# ---------------- EMAIL ----------------
def send_email(to):
    try:
        sender = "tubitaktest0@gmail.com"   # kendi mailin
        password = "umdyxtmpeljhodhy"          # gmail app password

        message = "Subject: Risk Uyarısı\n\nYüksek riskli haber bulundu!"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, to, message)
        server.quit()
    except Exception as e:
        print("mail hata:", e)

# ---------------- ANALYZE ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text", "")
    score = fake_score(text)

    result = {
        "text": text,
        "risk": score
    }

    data["news"].append(result)

    # yüksek riskte mail
    if score > 70:
        send_email("rumeyysauslu@gmail.com")

    return result

# ---------------- NEWS ----------------
@app.route("/api/news")
def news():
    url = "https://newsapi.org/v2/top-headlines?country=tr&apiKey=YOUR_API_KEY"

    try:
        res = requests.get(url).json()
        articles = res.get("articles", [])[:5]

        result = []
        for a in articles:
            title = a.get("title", "")
            result.append({
                "title": title,
                "risk": fake_score(title)
            })

        return {"news": result}
    except:
        return {"news": []}

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    return render_template_string("""
    <h1>Risk Panel</h1>

    <input id="txt">
    <button onclick="gonder()">Analiz</button>

    <p id="res"></p>

    <h2>Haberler</h2>
    <div id="news"></div>

    <script>
    async function gonder(){
        let t = document.getElementById("txt").value;

        let r = await fetch("/api/analyze",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify({text:t})
        });

        let j = await r.json();
        document.getElementById("res").innerText = "Risk: " + j.risk;
    }

    async function load(){
        let r = await fetch("/api/news");
        let j = await r.json();

        let html="";
        j.news.forEach(n=>{
            html += "<p>"+n.title+" ("+n.risk+")</p>";
        });

        document.getElementById("news").innerHTML = html;
    }

    setInterval(load,5000);
    </script>
    """)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return {"ok": True}

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()