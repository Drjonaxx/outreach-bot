from flask import Flask, render_template, request, jsonify
from analyzer.aggregator import run_all

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    keyword = (data.get("keyword") or "").strip()
    if not keyword:
        return jsonify({"error": "Ingresa un tema"}), 400
    results = run_all(keyword)
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True)
