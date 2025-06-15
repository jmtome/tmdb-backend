from flask import Flask, jsonify, request
from flask_cors import CORS
import requests, os, json
from dotenv import load_dotenv
from cache import get_with_stale_while_revalidate, init_db
from config import get_ttl

load_dotenv()

app = Flask(__name__)
CORS(app)
TMDB_KEY = os.environ.get("TMDB_KEY")
init_db()

def fetch_popular_movies():
    """Fetch popular movies from TMDB API"""
    res = requests.get(
        "https://api.themoviedb.org/3/movie/popular",
        headers={"Authorization": f"Bearer {TMDB_KEY}"}
    )
    if res.status_code == 200:
        return res.json()
    return None

def fetch_now_playing_movies():
    """Fetch now playing movies from TMDB API"""
    res = requests.get(
        "https://api.themoviedb.org/3/movie/now_playing",
        headers={"Authorization": f"Bearer {TMDB_KEY}"}
    )
    if res.status_code == 200:
        return res.json()
    return None

def fetch_upcoming_movies():
    """Fetch upcoming movies from TMDB API"""
    res = requests.get(
        "https://api.themoviedb.org/3/movie/upcoming",
        headers={"Authorization": f"Bearer {TMDB_KEY}"}
    )
    if res.status_code == 200:
        return res.json()
    return None

def fetch_trending_movies():
    """Fetch trending movies from TMDB API"""
    res = requests.get(
        "https://api.themoviedb.org/3/trending/movie/week",
        headers={"Authorization": f"Bearer {TMDB_KEY}"}
    )
    if res.status_code == 200:
        return res.json()
    return None

def fetch_movie_search(query):
    """Fetch movie search results from TMDB API"""
    url = "https://api.themoviedb.org/3/search/movie"
    headers = {"Authorization": f"Bearer {TMDB_KEY}"}
    params = {"query": query}
    
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        return res.json()
    return None

def fetch_tv_search(query):
    """Fetch TV search results from TMDB API"""
    url = "https://api.themoviedb.org/3/search/tv"
    headers = {"Authorization": f"Bearer {TMDB_KEY}"}
    params = {"query": query}
    
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        return res.json()
    return None

def fetch_movie_detail(movie_id):
    """Fetch complete movie details from TMDB API"""
    headers = {"Authorization": f"Bearer {TMDB_KEY}"}

    # Get movie details
    detail_res = requests.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}",
        headers=headers
    )
    if detail_res.status_code != 200:
        return None
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

    # Get streaming providers (powered by JustWatch)
    streaming_providers = {}
    try:
        providers_res = requests.get(
            f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers",
            headers=headers
        )
        print(f"Streaming providers API status: {providers_res.status_code}")
        
        if providers_res.status_code == 200:
            providers_data = providers_res.json()
            print(f"Raw providers data: {providers_data}")
            
            # Extract results by country - you can filter for specific countries if needed
            streaming_providers = providers_data.get("results", {})
            print(f"Countries available: {list(streaming_providers.keys())}")
            
            # Process providers for easier frontend consumption
            # Focus on major countries/regions - you can customize this list
            processed_providers = {}
            for country_code, country_data in streaming_providers.items():
                country_providers = {}
                
                # Streaming (flatrate) providers
                if "flatrate" in country_data:
                    country_providers["streaming"] = [
                        {
                            "provider_id": provider["provider_id"],
                            "provider_name": provider["provider_name"],
                            "logo_path": f"https://image.tmdb.org/t/p/original{provider['logo_path']}" if provider.get("logo_path") else None
                        }
                        for provider in country_data["flatrate"]
                    ]
                
                # Rental providers
                if "rent" in country_data:
                    country_providers["rent"] = [
                        {
                            "provider_id": provider["provider_id"],
                            "provider_name": provider["provider_name"],
                            "logo_path": f"https://image.tmdb.org/t/p/original{provider['logo_path']}" if provider.get("logo_path") else None
                        }
                        for provider in country_data["rent"]
                    ]
                
                # Purchase providers
                if "buy" in country_data:
                    country_providers["buy"] = [
                        {
                            "provider_id": provider["provider_id"],
                            "provider_name": provider["provider_name"],
                            "logo_path": f"https://image.tmdb.org/t/p/original{provider['logo_path']}" if provider.get("logo_path") else None
                        }
                        for provider in country_data["buy"]
                    ]
                
                # Add TMDB link for attribution (required by JustWatch terms)
                if "link" in country_data:
                    country_providers["tmdb_link"] = country_data["link"]
                
                if country_providers:  # Only add if there are providers
                    processed_providers[country_code] = country_providers
            
            streaming_providers = processed_providers
            print(f"Final processed providers: {streaming_providers}")
        else:
            print(f"Streaming providers API failed with status: {providers_res.status_code}")
            print(f"Response text: {providers_res.text}")
            streaming_providers = {}
    except Exception as e:
        print(f"Error fetching streaming providers: {e}")
        streaming_providers = {}

    return {
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
        "streaming_providers": streaming_providers,
    }

def fetch_movie_images(movie_id):
    """Fetch movie images from TMDB API"""
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/images"
    headers = {"Authorization": f"Bearer {TMDB_KEY}"}

    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return None

    data = res.json()
    backdrops = data.get("backdrops", [])

    return [
        {
            "file_path": img["file_path"],
            "width": img["width"],
            "height": img["height"]
        }
        for img in backdrops
    ]

def fetch_actor_detail(person_id):
    """Fetch actor details from TMDB API"""
    headers = {"Authorization": f"Bearer {TMDB_KEY}"}
    
    # Get actor details
    detail_res = requests.get(
        f"https://api.themoviedb.org/3/person/{person_id}",
        headers=headers
    )
    if detail_res.status_code != 200:
        return None
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
    
    return {
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

@app.route("/popular")
def popular():
    data, is_cached = get_with_stale_while_revalidate(
        key="popular",
        ttl_seconds=get_ttl("list", "popular"),
        fetch_function=fetch_popular_movies
    )
    
    if data:
        return jsonify(data)
    else:
        return {"error": "Failed to fetch popular movies"}, 500


@app.route("/now_playing")
def now_playing():
    data, is_cached = get_with_stale_while_revalidate(
        key="now_playing",
        ttl_seconds=get_ttl("list", "now_playing"),
        fetch_function=fetch_now_playing_movies
    )
    
    if data:
        return jsonify(data)
    else:
        return {"error": "Failed to fetch now playing movies"}, 500


@app.route("/upcoming")
def upcoming():
    data, is_cached = get_with_stale_while_revalidate(
        key="upcoming",
        ttl_seconds=get_ttl("list", "upcoming"),
        fetch_function=fetch_upcoming_movies
    )
    
    if data:
        return jsonify(data)
    else:
        return {"error": "Failed to fetch upcoming movies"}, 500


@app.route("/trending")
def trending():
    data, is_cached = get_with_stale_while_revalidate(
        key="trending",
        ttl_seconds=get_ttl("list", "trending"),
        fetch_function=fetch_trending_movies
    )
    
    if data:
        return jsonify(data)
    else:
        return {"error": "Failed to fetch trending movies"}, 500


@app.route("/search/movie")
def search_movie():
    query = request.args.get("q")
    if not query:
        return {"error": "Missing 'q' parameter"}, 400

    data, is_cached = get_with_stale_while_revalidate(
        key=f"movie_search_{query}",
        ttl_seconds=get_ttl("search", "movie_search"),
        fetch_function=lambda: fetch_movie_search(query)
    )
    
    if data:
        return jsonify(data)
    else:
        return {"error": "Failed to search movies"}, 500


@app.route("/search/tv")
def search_tv():
    query = request.args.get("q")
    if not query:
        return {"error": "Missing 'q' parameter"}, 400

    data, is_cached = get_with_stale_while_revalidate(
        key=f"tv_search_{query}",
        ttl_seconds=get_ttl("search", "tv_search"),
        fetch_function=lambda: fetch_tv_search(query)
    )
    
    if data:
        return jsonify(data)
    else:
        return {"error": "Failed to search TV shows"}, 500


@app.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    data, is_cached = get_with_stale_while_revalidate(
        key=f"movie_detail_{movie_id}",
        ttl_seconds=get_ttl("detail", "movie_detail"),
        fetch_function=lambda: fetch_movie_detail(movie_id)
    )
    
    if data:
        return jsonify(data)
    else:
        return {"error": "Failed to fetch movie details"}, 500


@app.route("/movie/<int:movie_id>/images")
def movie_images(movie_id):
    data, is_cached = get_with_stale_while_revalidate(
        key=f"movie_images_{movie_id}",
        ttl_seconds=get_ttl("detail", "movie_images"),
        fetch_function=lambda: fetch_movie_images(movie_id)
    )
    
    if data:
        return jsonify(data)
    else:
        return {"error": "Failed to fetch images"}, 500


@app.route("/actor/<int:person_id>")
def actor_detail(person_id):
    data, is_cached = get_with_stale_while_revalidate(
        key=f"actor_detail_{person_id}",
        ttl_seconds=get_ttl("detail", "actor_detail"),
        fetch_function=lambda: fetch_actor_detail(person_id)
    )
    
    if data:
        return jsonify(data)
    else:
        return {"error": "Failed to fetch actor details"}, 500


@app.route("/")
def home():
    return "TMDB backend working!"


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == '__main__':
    app.run(debug=True)
