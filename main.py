from flask import Flask, request, jsonify, render_template_string
import requests
import smtplib
import os

app = Flask(__name__)

history = []

# ---------------- RISK ----------------
def fake_score(text):
    score = 0
    t = text.lower()

    keywords = ["şok","son dakika","inanılmaz","öldü","ifşa","gizli","gizemli"]

    for k in keywords:
        if k in t:
            score += 15

    if text.isupper():
        score += 20

    if len(text) < 20:
        score += 10

    return min(score,100)

# ---------------- EMAIL ----------------
def send_email(to):
    try:
        sender = os.getenv("tubitaktest0@gmail.com")
        password = os.getenv("umdyxtmpeljhodhy")

        if not sender:
            return

        msg = "Subject: Risk Uyarısı\n\nYüksek riskli içerik bulundu!"

        s = smtplib.SMTP("smtp.gmail.com",587)
        s.starttls()
        s.login(sender,password)
        s.sendmail(sender,to,msg)
        s.quit()

    except Exception as e:
        print("mail hata:",e)

# ---------------- ANALYZE ----------------
@app.route("/api/analyze",methods=["POST"])
def analyze():
    text = request.json.get("text","")
    score = fake_score(text)

    history.append(score)

    if score > 70:
        send_email("rumeyysauslu@gmail.com")

    return {"risk":score}

# ---------------- NEWS ----------------
@app.route("/api/news")
def news():
    key = os.getenv("NEWS_API_KEY")

    if not key:
        return {"news":[{"title":"API key yok","risk":0}]}

    url = f"https://newsapi.org/v2/top-headlines?country=tr&apiKey={key}"

    try:
        r = requests.get(url).json()
        arts = r.get("articles",[])[:5]

        return {
            "news":[
                {"title":a["title"],"risk":fake_score(a["title"])}
                for a in arts
            ]
        }
    except:
        return {"news":[]}

# ---------------- TRENDS ----------------
@app.route("/api/trends")
def trends():
    try:
        r = requests.get("https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR").text
        items = r.split("<title>")[1:10]
        return {"trends":[i.split("</title>")[0] for i in items]}
    except:
        return {"trends":[]}

# ---------------- UI ----------------
@app.route("/")
def home():
    return render_template_string("""
    <h1>📊 Risk Paneli</h1>

    <input id="txt" placeholder="Haber gir">
    <button onclick="analyze()">Analiz</button>

    <h2 id="risk"></h2>

    <canvas id="chart"></canvas>

    <h3>📰 Haberler</h3>
    <div id="news"></div>

    <h3>🔥 Trendler</h3>
    <div id="trends"></div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <script>
    let chart;

    async function analyze(){
        let t=document.getElementById("txt").value;

        let r=await fetch("/api/analyze",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({text:t})
        });

        let j=await r.json();

        document.getElementById("risk").innerText="Risk: "+j.risk;

        draw(j.risk);
    }

    function draw(val){
        let ctx=document.getElementById("chart");

        if(chart) chart.destroy();

        chart=new Chart(ctx,{
            type:"bar",
            data:{
                labels:["Risk"],
                datasets:[{
                    label:"Risk Skoru",
                    data:[val]
                }]
            }
        });
    }

    async function loadNews(){
        let r=await fetch("/api/news");
        let j=await r.json();

        let h="";
        j.news.forEach(n=>{
            h+=`<p>${n.title} → ${n.risk}</p>`;
        });

        document.getElementById("news").innerHTML=h;
    }

    async function loadTrends(){
        let r=await fetch("/api/trends");
        let j=await r.json();

        let h="";
        j.trends.forEach(t=>{
            h+=`<p>${t}</p>`;
        });

        document.getElementById("trends").innerHTML=h;
    }

    loadNews();
    loadTrends();
    </script>
    """)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()