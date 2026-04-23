from flask import Flask, jsonify, request, render_template_string
import smtplib

app = Flask(__name__)

data = {
    "risk": 20,
    "status": "normal",
    "news": []
}

# ANA
@app.route("/")
def home():
    return {"ok": True}

# VERİ API
@app.route("/api/data")
def get_data():
    return jsonify(data)

# SAHTE HABER ANALİZİ (demo)
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text", "").lower()

    if "ölüm" in text or "şok" in text or "son dakika" in text:
        risk = 80
        status = "danger"
    else:
        risk = 20
        status = "normal"

    result = {"text": text, "risk": risk, "status": status}
    data["news"].append(result)
    data["risk"] = risk
    data["status"] = status

    return result

# EMAIL GÖNDERME
@app.route("/api/email", methods=["POST"])
def send_email():
    try:
        SENDER = "tubitaktest0@gmail.com"
        PASSWORD = "umdyxtmpeljhodhy"
        RECEIVER = "rumeyysauslu@gmail.com"
        message = "Subject: Risk Alert\n\nRisk seviyesi yükseldi!"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, message)
        server.quit()

        return {"sent": True}
    except Exception as e:
        return {"error": str(e)}

# PANEL
@app.route("/panel")
def panel():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Risk Panel</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h1>Risk Panel</h1>

        <input id="newsInput" placeholder="Haber gir">
        <button onclick="analyze()">Analiz Et</button>

        <p id="result"></p>

        <canvas id="chart" width="400" height="200"></canvas>

        <script>
        let chart;

        async function loadData() {
            const res = await fetch('/api/data');
            const json = await res.json();

            if (!chart) {
                chart = new Chart(document.getElementById('chart'), {
                    type: 'line',
                    data: {
                        labels: json.news.map((_, i) => i+1),
                        datasets: [{
                            label: 'Risk',
                            data: json.news.map(n => n.risk)
                        }]
                    }
                });
            } else {
                chart.data.labels = json.news.map((_, i) => i+1);
                chart.data.datasets[0].data = json.news.map(n => n.risk);
                chart.update();
            }
        }

        async function analyze() {
            const text = document.getElementById('newsInput').value;

            const res = await fetch('/api/analyze', {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({text})
            });

            const json = await res.json();
            document.getElementById('result').innerHTML =
                "Risk: " + json.risk + " (" + json.status + ")";

            loadData();
        }

        setInterval(loadData, 3000);
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run()