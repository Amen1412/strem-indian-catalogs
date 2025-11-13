from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import sys
import os

# Import utils - try different paths for Vercel compatibility
try:
    from api.utils import (
        load_cache,
        to_stremio_meta,
        get_enabled_languages,
        parse_catalog_id,
    )
except ImportError:
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from api.utils import (
        load_cache,
        to_stremio_meta,
        get_enabled_languages,
        parse_catalog_id,
    )

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Extract catalog id (contains language + token)
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        catalog_id = query_params.get('id', [None])[0] or query_params.get('lang', [None])[0]

        if not catalog_id:
            path_parts = self.path.split('/')
            if 'movie' in path_parts:
                idx = path_parts.index('movie')
                if idx + 1 < len(path_parts):
                    catalog_id = path_parts[idx + 1].replace('.json', '')

        if not catalog_id:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"metas": [], "error": "missing_catalog_id"}).encode())
            return

        lang, token = parse_catalog_id(catalog_id)

        enabled_languages = get_enabled_languages(token)
        if lang not in enabled_languages:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"metas": []}).encode())
            return

        print(f"[INFO] Catalog requested for {lang}")

        try:
            from api.utils import get_tmdb_key, fetch_movies_for_language, save_cache
            
            cached_movies = load_cache(lang, token)
            
            # If cache is empty, try to fetch (this handles cold starts)
            if not cached_movies:
                print(f"[INFO] Cache empty for {lang}, fetching movies...")
                tmdb_key = get_tmdb_key(token)
                if tmdb_key:
                    try:
                        cached_movies = fetch_movies_for_language(lang, tmdb_key)
                        save_cache(lang, cached_movies, token)
                    except Exception as e:
                        print(f"[ERROR] Failed to fetch movies for {lang}: {e}")
            
            metas = [meta for meta in (to_stremio_meta(m) for m in cached_movies) if meta]
            print(f"[INFO] Returning {len(metas)} total movies for {lang} ✅")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"metas": metas}).encode())
        except Exception as e:
            import traceback
            print(f"[ERROR] Catalog error: {traceback.format_exc()}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"metas": []}).encode())
        return

