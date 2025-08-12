#!/usr/bin/env python3
"""
Simple launcher script for the Multi-Screen Display Server
"""

import sys
import os

# Add the endpoints directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'endpoints'))

# Import and run the Flask app
from flask_app import app

if __name__ == '__main__':
    print("🚀 Starting Multi-Screen Display Server...")
    print("📍 Server will be available at: http://0.0.0.0:5000")
    print("🔧 Press Ctrl+C to stop the server")
    print()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
