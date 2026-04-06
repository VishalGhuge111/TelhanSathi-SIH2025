# CRITICAL: Monkey-patch eventlet BEFORE all other imports
try:
    import eventlet
    eventlet.monkey_patch()
except (ImportError, AttributeError):
    # eventlet not required if not installed or incompatible with Python version
    pass

from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

# Create db instance without app context to avoid circular imports
db = SQLAlchemy()

# Create SocketIO instance without app context to avoid circular imports
# Note: async_mode will be set in app.py's init_app call based on environment
socketio = SocketIO(
    cors_allowed_origins="*",      # Allow all origins (adjust in production)
    ping_timeout=60,
    ping_interval=25,
    logger=False,                   # Reduce logging noise
    engineio_logger=False,          # Reduce EngineIO logging
    allow_upgrades=True,            # Allow WebSocket upgrades
    engineio_kwargs={
        'allow_upgrades': True,     # Allow transport upgrades (polling to WebSocket)
        'handle_upgrade': True,     # Properly handle upgrade requests
    }
)
