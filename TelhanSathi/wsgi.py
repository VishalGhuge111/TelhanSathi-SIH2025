"""
WSGI entry point for production deployment
"""
import os

# Monkey-patch eventlet FIRST before importing app (if available and compatible)
try:
    import eventlet
    eventlet.monkey_patch()
except (ImportError, AttributeError):
    # eventlet not available or incompatible with Python version - use threading mode
    pass

from app import app, socketio, start_scheduler

# Start the background scheduler for production
start_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Use socketio.run() instead of app.run() to properly handle WebSocket connections
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        allow_unsafe_werkzeug=True
    )
