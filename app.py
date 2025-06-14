from cache import get_cached_result, save_cached_result, init_db
from flask import Flask, jsonify, request
import requests, os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
TMDB_KEY = os.environ.get("TMDB_KEY")

init_db()  # initialize SQLite cache table on startup


@app.route("/popular")
def popular():
    res = requests.get(
        "https://api.themoviedb.org/3/movie/popular",
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
        print(f"[CACHE] HIT: '{query}' (movie)")
        return jsonify(cached)

    print(f"[CACHE] MISS: '{query}' (movie)")
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
        print(f"[CACHE] HIT: '{query}' (tv)")
        return jsonify(cached)

    print(f"[CACHE] MISS: '{query}' (tv)")
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
