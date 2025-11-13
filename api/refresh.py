from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import sys
import os

# Import utils - try different paths for Vercel compatibility
try:
    from api.utils import (
        get_tmdb_key, get_enabled_languages, 
        fetch_movies_for_language, save_cache
    )
except ImportError:
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from api.utils import (
        get_tmdb_key, get_enabled_languages, 
        fetch_movies_for_language, save_cache
    )

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        token = query_params.get('token', [None])[0]

        tmdb_key = get_tmdb_key(token)
        if not tmdb_key:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "TMDB API key not configured"
            }).encode())
            return
        
        enabled_languages = get_enabled_languages(token)
        
        def do_refresh():
            try:
                for lang in enabled_languages:
                    print(f"[REFRESH] Refreshing {lang}...")
                    movies = fetch_movies_for_language(lang, tmdb_key)
                    save_cache(lang, movies, token)
                print("[REFRESH] Background refresh complete ✅")
            except Exception as e:
                import traceback
                print(f"[REFRESH ERROR] {traceback.format_exc()}")
        
        # Run refresh in background (for Vercel, this will complete before response)
        try:
            do_refresh()
            status = "refresh completed"
        except Exception as e:
            status = f"refresh error: {str(e)}"
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {"status": status}
        if token:
            response["token"] = token
        self.wfile.write(json.dumps(response).encode())
        return

