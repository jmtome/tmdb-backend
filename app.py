from flask import Flask, jsonify, request
from flask_cors import CORS
import requests, os
from dotenv import load_dotenv
from cache import get_cached_result, save_cached_result, get_cached_data, save_cached_data, init_db

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


@app.route("/trending")
def trending():
    res = requests.get(
        "https://api.themoviedb.org/3/trending/movie/week",
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


@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    # Check cache first
    cache_key = f"movie_detail_{movie_id}"
    cached = get_cached_data(cache_key, "movie_detail")
    if cached:
        return jsonify(cached)

    headers = {"Authorization": f"Bearer {TMDB_KEY}"}

    # Get movie details
    detail_res = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}",
        headers=headers
    )
    if detail_res.status_code != 200:
        return {"error": "Failed to fetch movie details"}, 500
    details = detail_res.json()

    # Get images
    images_res = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}/images",
        headers=headers
    )
    if images_res.status_code == 200:
        images = images_res.json().get("backdrops", [])
        backdrops = [
            f"https://image.tmdb.org/t/p/original{img['file_path']}" for img in images[:10]
        ]
    else:
        backdrops = []

    # Get credits
    credits_res = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}/credits",
        headers=headers
    )
    if credits_res.status_code == 200:
        credits = credits_res.json()
        cast = credits.get("cast", [])[:10]
        crew = credits.get("crew", [])
        director = next((p for p in crew if p.get("job") == "Director"), None)
    else:
        cast = []
        director = None

    # Get videos (trailers, teasers, etc.)
    videos_res = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}/videos",
        headers=headers
    )
    youtube_videos = []
    if videos_res.status_code == 200:
        videos_data = videos_res.json()
        all_videos = videos_data.get("results", [])
        
        # Filter for YouTube videos and prioritize trailers
        youtube_videos = [
            {
                "key": video["key"],
                "name": video["name"],
                "type": video["type"],
                "official": video.get("official", False),
                "youtube_url": f"https://www.youtube.com/watch?v={video['key']}"
            }
            for video in all_videos
            if video.get("site") == "YouTube"
        ]
        
        # Sort videos: official trailers first, then other trailers, then other types
        youtube_videos.sort(key=lambda x: (
            not x["official"],  # Official videos first
            x["type"] != "Trailer",  # Trailers before other types
            x["type"] != "Teaser"  # Teasers after trailers
        ))

    result = {
        "id": details.get("id"),
        "title": details.get("title"),
        "overview": details.get("overview"),
        "poster_path": details.get("poster_path"),
        "release_date": details.get("release_date"),
        "vote_average": details.get("vote_average"),
        "vote_count": details.get("vote_count"),
        "genres": details.get("genres", []),
        "backdrops": backdrops,
        "cast": cast,
        "director": director,
        "youtube_videos": youtube_videos,
    }

    # Save to cache
    save_cached_data(cache_key, "movie_detail", result)
    return jsonify(result)


@app.route("/movie/<int:movie_id>/images")
def movie_images(movie_id):
    # Check cache first
    cache_key = f"movie_images_{movie_id}"
    cached = get_cached_data(cache_key, "movie_images")
    if cached:
        return jsonify(cached)

    url = f"https://api.themoviedb.org/3/movie/{movie_id}/images"
    headers = {"Authorization": f"Bearer {TMDB_KEY}"}

    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return {"error": "Failed to fetch images"}, res.status_code

    data = res.json()
    backdrops = data.get("backdrops", [])

    simplified = [
        {
            "file_path": img["file_path"],
            "width": img["width"],
            "height": img["height"]
        }
        for img in backdrops
    ]

    # Save to cache
    save_cached_data(cache_key, "movie_images", simplified)
    return jsonify(simplified)


@app.route("/actor/<int:person_id>")
def actor_detail(person_id):
    # Check cache first
    cache_key = f"actor_detail_{person_id}"
    cached = get_cached_data(cache_key, "actor_detail")
    if cached:
        return jsonify(cached)

    headers = {"Authorization": f"Bearer {TMDB_KEY}"}
    # Get actor details
    detail_res = requests.get(
        f"https://api.themoviedb.org/3/person/{person_id}",
        headers=headers
    )
    if detail_res.status_code != 200:
        return {"error": "Failed to fetch actor details"}, 500
    details = detail_res.json()

    # Get movie credits
    credits_res = requests.get(
        f"https://api.themoviedb.org/3/person/{person_id}/movie_credits",
        headers=headers
    )
    movies = []
    if credits_res.status_code == 200:
        credits = credits_res.json()
        movies = sorted(
            credits.get("cast", []),
            key=lambda m: m.get("popularity", 0),
            reverse=True
        )
    
    result = {
        "id": details.get("id"),
        "name": details.get("name"),
        "biography": details.get("biography"),
        "profile_path": details.get("profile_path"),
        "birthday": details.get("birthday"),
        "place_of_birth": details.get("place_of_birth"),
        "known_for_department": details.get("known_for_department"),
        "movies": [
            {
                "id": m["id"],
                "title": m["title"],
                "poster_path": m["poster_path"],
                "character": m.get("character"),
                "release_date": m.get("release_date"),
            }
            for m in movies if m.get("poster_path")
        ]
    }

    # Save to cache
    save_cached_data(cache_key, "actor_detail", result)
    return jsonify(result)


@app.route("/")
def home():
    return "TMDB backend working!"


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == '__main__':
    app.run(debug=True)
