from flask import Flask, request, jsonify, render_template_string
from db import get_conn, init_db
from model import ai_score
import os, smtplib

app = Flask(__name__)
init_db()

# ---------------- EMAIL ----------------
def send_email(text, risk):
    try:
        user = os.getenv("tubitaktest0@gmail.com")
        pw = os.getenv("umdyxtmpeljhodhy")
        to = os.getenv("rumeyysauslu@gmail.com")

        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(user, pw)

        msg = f"Subject: 🚨 Yüksek Risk\n\n{text}\nRisk: {risk}%"
        s.sendmail(user, to, msg)
        s.quit()
    except:
        pass

# ---------------- API ----------------
@app.route("/api/news")
def news():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT text,risk,source,link FROM news ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return {"data":[{"text":r[0],"risk":r[1],"source":r[2],"link":r[3]} for r in rows]}

@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text")

    if not text or len(text) < 20:
        return {"error":"Haber metni gir!"}

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
</head>
<body style="background:#020617;color:white">

<h1>ULTRA PRO AI</h1>

<input id="txt">
<button onclick="analyze()">Analiz</button>
<h3 id="res"></h3>

<canvas id="chart"></canvas>
<div id="news"></div>

<script>
let chart;

async function analyze(){
 let t=txt.value;

 let r=await fetch("/api/analyze",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({text:t})
 });

 let j=await r.json();

 if(j.error){res.innerHTML=j.error;return;}

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
  html+=`<p>${n.text} - ${n.risk}%</p>`;
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