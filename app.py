from flask import Flask, jsonify
import requests, os

app = Flask(__name__)
TMDB_KEY = os.environ.get("TMDB_KEY")

@app.route("/popular")
def popular():
    res = requests.get(
        "https://api.themoviedb.org/3/movie/popular",
        headers={"Authorization": f"Bearer {TMDB_KEY}"}
    )
    return jsonify(res.json())

@app.route("/")
def home():
    return "TMDB backend working!"

@app.route("/health")
def health():
    return {"status": "ok"}
