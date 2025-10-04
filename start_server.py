#!/usr/bin/env python3
"""
Simple HTTP server to serve the dashboard with CORS support
"""
import http.server
import socketserver
import os
from pathlib import Path

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def start_server(port=8000):
    """Start HTTP server for dashboard"""
    os.chdir(Path(__file__).parent)

    with socketserver.TCPServer(("", port), CORSHTTPRequestHandler) as httpd:
        print(f"Dashboard server running at:")
        print(f"🌐 http://localhost:{port}/dashboard.html")
        print(f"📊 Tracking data: http://localhost:{port}/tracking.json")
        print()
        print("Press Ctrl+C to stop the server")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    start_server()