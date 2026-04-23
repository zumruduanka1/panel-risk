from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# örnek veri (sonra API ile değiştiririz)
data = {
    "risk": 42,
    "status": "normal"
}

# ana sayfa
@app.route("/")
def home():
    return {"ok": True}

# API (veri çekmek için)
@app.route("/api/data")
def get_data():
    return jsonify(data)

# veri güncelleme (POST)
@app.route("/api/update", methods=["POST"])
def update_data():
    global data
    data = request.json
    return {"success": True, "new_data": data}

# PANEL (HTML arayüz)
@app.route("/panel")
def panel():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Risk Panel</title>
    </head>
    <body>
        <h1>Risk Panel</h1>
        <div id="data"></div>

        <script>
        async function loadData() {
            const res = await fetch('/api/data');
            const json = await res.json();
            document.getElementById('data').innerHTML =
                "Risk: " + json.risk + "<br>Status: " + json.status;
        }

        loadData();
        setInterval(loadData, 3000); // 3 sn'de bir günceller
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run(debug=True)