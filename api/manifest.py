from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import sys
import os

# Import utils - try different paths for Vercel compatibility
try:
    from api.utils import (
        get_enabled_languages,
        LANGUAGE_NAMES,
        build_catalog_id,
        load_config,
    )
except ImportError:
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from api.utils import (
        get_enabled_languages,
        LANGUAGE_NAMES,
        build_catalog_id,
        load_config,
    )

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Get the full path including query string
            full_path = self.path
            if '?' not in full_path and self.headers.get('X-Vercel-Forwarded-Query'):
                full_path = f"{full_path}?{self.headers.get('X-Vercel-Forwarded-Query')}"
            
            parsed_url = urlparse(full_path)
            query_params = parse_qs(parsed_url.query)
            token = query_params.get("token", [None])[0]

            # Also check for token in path (for /manifest/<token>.json format)
            if not token and parsed_url.path.startswith("/manifest/"):
                maybe_token = os.path.splitext(os.path.basename(parsed_url.path))[0]
                if maybe_token and maybe_token != "manifest":
                    token = maybe_token

            # When no token is provided (direct /manifest.json), fall back to default config.
            config = load_config(token)
            enabled_languages = config.get("enabled_languages", ["malayalam"])
            
            # Ensure we have at least one language
            if not enabled_languages or not isinstance(enabled_languages, list):
                enabled_languages = ["malayalam"]

            catalogs = []
            for lang in enabled_languages:
                if lang in LANGUAGE_NAMES:
                    catalogs.append({
                        "type": "movie",
                        "id": build_catalog_id(lang, token),
                        "name": LANGUAGE_NAMES[lang]
                    })
            
            # Ensure we have at least one catalog
            if not catalogs:
                catalogs = [{
                    "type": "movie",
                    "id": build_catalog_id("malayalam", token),
                    "name": "Malayalam"
                }]

            if token:
                manifest_id = f"org.indian.catalog.{token[:8]}"
            else:
                manifest_id = "org.indian.catalog"

            manifest = {
                "id": manifest_id,
                "version": "2.0.0",
                "name": "Indian Movies OTT",
                "description": "Latest Indian Movies on OTT Platforms",
                "resources": ["catalog"],
                "types": ["movie"],
                "catalogs": catalogs,
                "idPrefixes": ["tt"]
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(manifest, indent=None, separators=(',', ':')).encode())
        except Exception as e:
            import traceback
            print(f"[ERROR] Manifest error: {traceback.format_exc()}")
            # Return a minimal valid manifest even on error
            error_manifest = {
                "id": "org.indian.catalog",
                "version": "2.0.0",
                "name": "Indian Movies OTT",
                "description": "Latest Indian Movies on OTT Platforms",
                "resources": ["catalog"],
                "types": ["movie"],
                "catalogs": [{
                    "type": "movie",
                    "id": "malayalam",
                    "name": "Malayalam"
                }],
                "idPrefixes": ["tt"]
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_manifest, indent=None, separators=(',', ':')).encode())
        return

