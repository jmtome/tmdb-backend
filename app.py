from flask_cors import CORS
from flask import Flask, jsonify, request
import requests, os
from dotenv import load_dotenv
from cache import get_cached_result, save_cached_result, init_db

load_dotenv()

app = Flask(__name__)
CORS(app)
TMDB_KEY = os.environ.get("TMDB_KEY")

init_db()

@app.route("/popular")
def popular():
    res = requests.get(
        "https://api.themoviedb.org/3/movie/popular",
        headers={"Authorization": f"Bearer {TMDB_KEY}"}
    )
    return jsonify(res.json())

@app.route("/trending")
def trending():
    res = requests.get(
        "https://api.themoviedb.org/3/trending/movie/day",
        headers={"Authorization": f"Bearer {TMDB_KEY}"}
    )
    return jsonify(res.json())

@app.route("/now_playing")
def now_playing():
    res = requests.get(
        "https://api.themoviedb.org/3/movie/now_playing",
        headers={"Authorization": f"Bearer {TMDB_KEY}"}
    )
    return jsonify(res.json())

@app.route("/upcoming")
def upcoming():
    res = requests.get(
        "https://api.themoviedb.org/3/movie/upcoming",
        headers={"Authorization": f"Bearer {TMDB_KEY}"}
    )
    return jsonify(res.json())


@app.route("/search/movie")
def search_movie():
    query = request.args.get("q")
    if not query:
        return {"error": "Missing 'q' parameter"}, 400

    cached = get_cached_result(query, "movie")
    if cached:
        return jsonify(cached)

    url = "https://api.themoviedb.org/3/search/movie"
    headers = {"Authorization": f"Bearer {TMDB_KEY}"}
    params = {"query": query}
    res = requests.get(url, headers=headers, params=params)
    data = res.json()

    save_cached_result(query, "movie", data)
    return jsonify(data)

@app.route("/search/tv")
def search_tv():
    query = request.args.get("q")
    if not query:
        return {"error": "Missing 'q' parameter"}, 400

    cached = get_cached_result(query, "tv")
    if cached:
        return jsonify(cached)

    url = "https://api.themoviedb.org/3/search/tv"
    headers = {"Authorization": f"Bearer {TMDB_KEY}"}
    params = {"query": query}
    res = requests.get(url, headers=headers, params=params)
    data = res.json()

    save_cached_result(query, "tv", data)
    return jsonify(data)

@app.route("/")
def home():
    return "TMDB backend working!"

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == '__main__':
    app.run(debug=True)
