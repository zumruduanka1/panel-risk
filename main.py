from flask import Flask, request, jsonify, render_template_string
import random, time, os

app = Flask(__name__)

# ---------------- HABER KONTROL ----------------
def is_news(text):
    if not text or len(text) < 40:
        return False

    keywords = ["son dakika","iddia","haber","gündem","açıklandı","rapor","uzman"]

    return any(k in text.lower() for k in keywords)

# ---------------- ANALİZ ----------------
def analyze_news(text):
    t = text.lower()
    score = 10

    # clickbait
    if any(k in t for k in ["şok","ifşa","gizli","inanılmaz"]):
        score += 30

    # iddia
    if "iddia" in t:
        score += 20

    # viral
    if any(k in t for k in ["herkes","viral"]):
        score += 15

    # kesinlik
    if "kanıtlandı" in t:
        score += 25

    # güven düşür
    if any(k in t for k in ["uzman","rapor","resmi"]):
        score -= 20

    score = max(5, min(100, score))

    return score

# ---------------- API ----------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()

    if not data or "text" not in data:
        return jsonify({"error": "veri yok"})

    text = data["text"]

    if not is_news(text):
        return jsonify({"error": "Bu bir haber metni değil!"})

    r = analyze_news(text)

    return jsonify({
        "risk": r,
        "status": "ok"
    })

# ---------------- UI ----------------
@app.route("/")
def home():
    return render_template_string("""
    <html>
    <body style="background:black;color:white;font-family:Arial">

    <h1>Fake News Analyzer</h1>

    <input id="txt" style="width:300px">
    <button onclick="go()">Analiz</button>

    <h2 id="res"></h2>

    <script>
    async function go(){
        let text = document.getElementById("txt").value;

        let r = await fetch("/api/analyze", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({text:text})
        });

        let j = await r.json();

        if(j.error){
            document.getElementById("res").innerHTML = "❌ " + j.error;
        }else{
            document.getElementById("res").innerHTML = "Risk: " + j.risk + "%";
        }
    }
    </script>

    </body>
    </html>
    """)

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)