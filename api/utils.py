import base64
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import requests

TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Language codes mapping
LANGUAGE_CODES = {
    "malayalam": "ml",
    "hindi": "hi",
    "tamil": "ta",
    "kannada": "kn"
}

LANGUAGE_NAMES = {
    "malayalam": "Malayalam",
    "hindi": "Hindi",
    "tamil": "Tamil",
    "kannada": "Kannada"
}

CATALOG_ID_SEPARATOR = "~"


def build_catalog_id(language, token):
    return f"{language}{CATALOG_ID_SEPARATOR}{token}" if token else language


def parse_catalog_id(catalog_id):
    if CATALOG_ID_SEPARATOR in catalog_id:
        lang, token = catalog_id.split(CATALOG_ID_SEPARATOR, 1)
        return lang, token
    return catalog_id, None

def get_config_path():
    """Get path to config file"""
    # Use /tmp for Vercel serverless functions
    config_dir = Path("/tmp")
    try:
        config_dir.mkdir(exist_ok=True)
    except:
        pass
    return config_dir / "stremio_config.json"

def encode_config_token(config):
    """Encode a configuration dict into a compact token."""
    normalized = {
        "tmdb_api_key": config.get("tmdb_api_key", "").strip(),
        "enabled_languages": sorted(
            {lang for lang in config.get("enabled_languages", []) if lang in LANGUAGE_CODES}
        )
        or ["malayalam"],
    }
    payload = json.dumps(normalized, separators=(",", ":"))
    token = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return token


def decode_config_token(token):
    """Decode a configuration token back into a dict."""
    if not token:
        return {"tmdb_api_key": "", "enabled_languages": ["malayalam"]}

    try:
        padding = "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(f"{token}{padding}".encode()).decode()
        data = json.loads(decoded)
        tmdb_key = data.get("tmdb_api_key", "").strip()
        enabled_languages = data.get("enabled_languages", ["malayalam"])
        if not isinstance(enabled_languages, list):
            enabled_languages = ["malayalam"]
        enabled_languages = [
            lang for lang in enabled_languages if lang in LANGUAGE_CODES
        ] or ["malayalam"]
        return {"tmdb_api_key": tmdb_key, "enabled_languages": enabled_languages}
    except Exception:
        return {"tmdb_api_key": "", "enabled_languages": ["malayalam"]}


def load_config(token=None):
    """Load user configuration"""
    if token:
        return decode_config_token(token)

    # Try to load from file first
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                # Merge with environment variables (env takes precedence for API key)
                return {
                    "tmdb_api_key": os.getenv('TMDB_API_KEY', file_config.get("tmdb_api_key", '')),
                    "enabled_languages": file_config.get("enabled_languages", ["malayalam"])
                }
        except:
            pass
    
    # Default config from environment variables
    enabled_langs = os.getenv('ENABLED_LANGUAGES', 'malayalam')
    if enabled_langs:
        enabled_langs = [lang.strip() for lang in enabled_langs.split(',')]
    else:
        enabled_langs = ["malayalam"]
    
    return {
        "tmdb_api_key": os.getenv('TMDB_API_KEY', ''),
        "enabled_languages": enabled_langs
    }

def save_config(config):
    """Save user configuration"""
    config_path = get_config_path()
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"[WARNING] Could not save config to file: {e}")
        # Config will still work via environment variables

def get_tmdb_key(token=None):
    """Get TMDB API key from config or env"""
    config = load_config(token)
    return config.get("tmdb_api_key") or os.getenv('TMDB_API_KEY', '')


def get_enabled_languages(token=None):
    """Get enabled languages from config"""
    config = load_config(token)
    return config.get("enabled_languages", ["malayalam"])

def fetch_movies_for_language(language_code, tmdb_key):
    """Fetch movies for a specific language"""
    print(f"[CACHE] Fetching {LANGUAGE_NAMES.get(language_code, language_code)} OTT movies...")
    
    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []
    
    lang_code = LANGUAGE_CODES.get(language_code, language_code)
    
    for page in range(1, 1000):
        print(f"[INFO] Checking page {page} for {language_code}")
        params = {
            "api_key": tmdb_key,
            "with_original_language": lang_code,
            "sort_by": "release_date.desc",
            "release_date.lte": today,
            "region": "IN",
            "page": page
        }
        
        try:
            response = requests.get(f"{TMDB_BASE_URL}/discover/movie", params=params, timeout=30)
            if response.status_code != 200:
                print(f"[ERROR] TMDB API error: {response.status_code}")
                break
                
            results = response.json().get("results", [])
            if not results:
                break
            
            for movie in results:
                movie_id = movie.get("id")
                title = movie.get("title")
                if not movie_id or not title:
                    continue
                
                # Check OTT availability
                try:
                    providers_url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers"
                    prov_response = requests.get(providers_url, params={"api_key": tmdb_key}, timeout=30)
                    prov_data = prov_response.json()
                    
                    if "results" in prov_data and "IN" in prov_data["results"]:
                        if "flatrate" in prov_data["results"]["IN"]:
                            # Now get IMDb ID
                            ext_url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
                            ext_response = requests.get(ext_url, params={"api_key": tmdb_key}, timeout=30)
                            ext_data = ext_response.json()
                            imdb_id = ext_data.get("imdb_id")
                            
                            if imdb_id and imdb_id.startswith("tt"):
                                movie["imdb_id"] = imdb_id
                                movie["language"] = language_code
                                final_movies.append(movie)
                except Exception as e:
                    print(f"[ERROR] Error checking OTT for movie {movie_id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"[ERROR] Page {page} failed: {e}")
            break
    
    # Deduplicate
    seen_ids = set()
    unique_movies = []
    for movie in final_movies:
        imdb_id = movie.get("imdb_id")
        if imdb_id and imdb_id not in seen_ids:
            seen_ids.add(imdb_id)
            unique_movies.append(movie)
    
    print(f"[CACHE] Fetched {len(unique_movies)} {LANGUAGE_NAMES.get(language_code, language_code)} OTT movies ✅")
    return unique_movies

def get_cache_path(language, token=None):
    """Get path to cache file for a language"""
    # Use /tmp for Vercel serverless functions
    cache_dir = Path("/tmp")
    try:
        cache_dir.mkdir(exist_ok=True)
    except:
        pass
    if token:
        token_hash = hashlib.sha1(token.encode()).hexdigest()[:10]
    else:
        token_hash = "default"
    return cache_dir / f"movies_cache_{language}_{token_hash}.json"


def save_cache(language, movies, token=None):
    """Save movies cache for a language"""
    cache_path = get_cache_path(language, token)
    try:
        with open(cache_path, 'w') as f:
            json.dump(movies, f)
    except Exception as e:
        print(f"[WARNING] Could not save cache for {language}: {e}")


def load_cache(language, token=None):
    """Load movies cache for a language"""
    cache_path = get_cache_path(language, token)
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except:
            pass
    return []

def to_stremio_meta(movie):
    """Convert movie to Stremio format"""
    try:
        imdb_id = movie.get("imdb_id")
        title = movie.get("title")
        if not imdb_id or not title:
            return None
        
        return {
            "id": imdb_id,
            "type": "movie",
            "name": title,
            "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
            "description": movie.get("overview", ""),
            "releaseInfo": movie.get("release_date", ""),
            "background": f"https://image.tmdb.org/t/p/w780{movie['backdrop_path']}" if movie.get("backdrop_path") else None
        }
    except Exception as e:
        print(f"[ERROR] to_stremio_meta failed: {e}")
        return None

