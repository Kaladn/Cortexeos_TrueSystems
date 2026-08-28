# Forest AI Production Console - UI Launcher
# Serves the web interface on http://localhost:8080

import http.server
import socketserver
import os
import sys

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        # Enable CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def main():
    print("🌲 Forest AI Production Console - UI Launcher")
    print("=" * 80)
    print(f"\n📂 Serving from: {DIRECTORY}")
    print(f"🌐 URL: http://localhost:{PORT}")
    print(f"\n✨ Features:")
    print("   - 6-1-6 Document Mapping")
    print("   - Unmapped Token Review")
    print("   - GPT-OSS Local LLM Integration")
    print("   - Lexicon Browser")
    print("   - Real-time Monitoring")
    print(f"\n{'=' * 80}")
    print("\n🚀 Starting server...")
    print(f"   Open your browser to: http://localhost:{PORT}/forest_ai_production.html")
    print("\n   Press Ctrl+C to stop\n")
    
    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
