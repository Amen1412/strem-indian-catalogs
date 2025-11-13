from http.server import BaseHTTPRequestHandler
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
        tmdb_key = get_tmdb_key()
        if not tmdb_key:
            print("[CRON] TMDB API key not configured, skipping refresh")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "skipped - no api key"}).encode())
            return
        
        enabled_languages = get_enabled_languages()
        
        try:
            for lang in enabled_languages:
                print(f"[CRON] Auto-refreshing {lang}...")
                movies = fetch_movies_for_language(lang, tmdb_key)
                save_cache(lang, movies)
            print("[CRON] Auto-refresh complete ✅")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            print(f"[CRON ERROR] {error_msg}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
        return

