"""
Local development server for testing OBS backend.
Run this instead of Vercel for local testing.
"""
from api.index import handler
from http.server import HTTPServer

if __name__ == "__main__":
    PORT = 8000
    server = HTTPServer(('localhost', PORT), handler)
    print(f"✅ Backend running on http://localhost:{PORT}")
    print(f"Test with: POST http://localhost:{PORT} with action=init_login or action=login")
    print("Press Ctrl+C to stop")
    server.serve_forever()
