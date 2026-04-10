"""
Open the BEI Dashboard in your default browser.

Usage:
    python serve.py          # starts on port 8080
    python serve.py 9000     # starts on a custom port
"""

import http.server
import sys
import threading
import webbrowser

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

handler = http.server.SimpleHTTPRequestHandler
handler.extensions_map.update({".json": "application/json", ".geojson": "application/geo+json"})

httpd = http.server.HTTPServer(("127.0.0.1", PORT), handler)
url = f"http://127.0.0.1:{PORT}"

print(f"Serving dashboard at {url}")
print("Press Ctrl+C to stop.\n")

threading.Timer(0.5, lambda: webbrowser.open(url)).start()

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nStopped.")
    httpd.server_close()
