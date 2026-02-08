"""
Local Runner Script.
Run this to start the backend locally: python scripts/run_local.py
"""
import sys
import os

# Add project root to path so we can import from api and modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import HTTPServer
from api.index import handler

if __name__ == "__main__":
    PORT = 8000
    server = HTTPServer(('localhost', PORT), handler)
    print(f"✅ Backend running on http://localhost:{PORT}")
    print(f"Test with: POST http://localhost:{PORT} with action=init_login")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()
