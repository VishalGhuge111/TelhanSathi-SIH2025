# CRITICAL: Monkey-patch eventlet BEFORE all other imports (including Flask)
eventlet_available = False
try:
    import eventlet
    eventlet.monkey_patch()
    print("[INIT] ✓ Eventlet monkey-patched successfully")
    eventlet_available = True
except (ImportError, AttributeError):
    # eventlet not available or incompatible with Python version (3.10+)
    print("[INIT] ⚠ Eventlet not available or incompatible - using threading mode")
    eventlet_available = False

from datetime import datetime
from flask import Flask, render_template, send_from_directory, url_for, redirect, session, request, g
from flask_cors import CORS
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
import requests
import logging

from extensions import db, socketio
from flask_migrate import Migrate  # ✅ Added
from models import *  # ✅ Import main models
from models_marketplace_keep import *

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Initialize SocketIO with Flask app
# Use proper WSGIServer configuration for WebSocket handling
socketio.init_app(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet' if eventlet_available else 'threading',
)

# ----------------------- BACKGROUND SCHEDULER (Keep Render App Active) -----------------------
scheduler = BackgroundScheduler()

# Configure scheduler with thread pool to avoid blocking WebSocket
scheduler_config = {
    'apscheduler.executors.default': {
        'type': 'threadpool',
        'max_workers': 1
    },
    'apscheduler.job_defaults.coalesce': True,
    'apscheduler.job_defaults.max_instances': 1,
}
scheduler.configure(scheduler_config)

def ping_app():
    """Ping the app to keep it active on Render."""
    try:
        # Get the app URL from environment or use localhost for development
        app_url = os.getenv('APP_URL', 'http://localhost:5000')
        response = requests.get(f'{app_url}/ping', timeout=5)
        if response.status_code == 200:
            print(f"[SCHEDULER] ✓ Pinged app at {datetime.utcnow().isoformat()}")
        else:
            print(f"[SCHEDULER] ⚠ Ping returned status {response.status_code}")
    except Exception as e:
        print(f"[SCHEDULER] ⚠ Failed to ping app: {str(e)}")

# Add the ping job - runs every 4 minutes
try:
    scheduler.add_job(ping_app, 'interval', minutes=4, id='app_pinger')
except Exception:
    pass  # Job might already exist

# Start scheduler in the context of the app
def start_scheduler():
    try:
        # Check if we're in development mode first (takes precedence)
        flask_env = os.getenv('FLASK_ENV', 'production').lower()
        
        if flask_env == 'development':
            print("[SCHEDULER] ℹ Development mode detected - scheduler disabled to avoid SocketIO conflicts")
            return
        
        # Only start scheduler on Render (production) when APP_URL is explicitly set to Render
        app_url = os.getenv('APP_URL', '')
        is_production = app_url and 'onrender.com' in app_url.lower()
        
        if not is_production:
            print("[SCHEDULER] ℹ Production mode but APP_URL not set to Render - scheduler disabled")
            return
            
        if not scheduler.running:
            scheduler.start()
            print(f"[SCHEDULER] ✓ Background scheduler started on Render - app will stay active")
    except Exception as e:
        print(f"[SCHEDULER] ⚠ Failed to start scheduler: {str(e)}")

# ----------------------- SESSION CONFIG -----------------------
app.config['SESSION_COOKIE_SECURE'] = False  # True only in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ----------------------- DATABASE CONFIG -----------------------
import re

database_url = os.getenv('DATABASE_URL', 'sqlite:///telhan_sathi.db')

# Handle internal Render PostgreSQL URL conversion
# Input:  postgresql://user:pass@dpg-xxxxx-a/dbname
# Output: postgresql+psycopg://user:pass@dpg-xxxxx-a.oregon-postgres.render.com/dbname
if database_url.startswith('postgresql://') and '@dpg-' in database_url:
    # Extract components
    match = re.match(r'postgresql://(.+)@(dpg-[a-z0-9-]+)/(.+)', database_url)
    if match:
        credentials = match.group(1)
        dpg_id = match.group(2)
        dbname = match.group(3)
        # Reconstruct with external endpoint if needed
        # Check if it's already external (has .render.com)
        if '.render.com' not in database_url:
            database_url = f'postgresql+psycopg://{credentials}@{dpg_id}.oregon-postgres.render.com/{dbname}?sslmode=require'
        else:
            # Already external, just convert dialect
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
            if '?sslmode' not in database_url:
                database_url += '?sslmode=require'
    else:
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        if '?sslmode' not in database_url:
            database_url += '?sslmode=require'
elif database_url.startswith('postgresql://'):
    # Simple conversion to psycopg dialect
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    if '?sslmode' not in database_url:
        database_url += '?sslmode=require'

# Debug: Print (without password)
db_url_debug = database_url.split('@')[0] + '@***:5432/...' if '@' in database_url else database_url
print(f"[CONFIG] Database URL configured (formatted): {db_url_debug}")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize the database
db.init_app(app)

# Initialize migrations
migrate = Migrate(app, db)

# Initialize database tables on app startup with better error handling
def init_db_tables():
    """Initialize database tables with extended retry logic"""
    import time
    max_retries = 10  # More retries for initial startup
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with app.app_context():
                print(f"[DB INIT] Attempt {retry_count + 1}/{max_retries}: Creating database tables...")
                db.create_all()
                print("[DB INIT] ✓ Database tables initialized successfully!")
                return True
        except Exception as e:
            retry_count += 1
            error_msg = str(e)
            if retry_count < max_retries:
                wait_time = 2 * retry_count  # 2s, 4s, 6s, ... exponential
                print(f"[DB INIT] ⚠ Connection failed: {type(e).__name__}")
                print(f"[DB INIT] Retrying in {wait_time} seconds... ({retry_count}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"[DB INIT] ⚠ Could not connect after {max_retries} attempts")
                print(f"[DB INIT] Database will be initialized on first request")
                return False

# Execute initialization
print("[APP] Starting database initialization...")
init_db_tables()


# ----------------------- BLUEPRINTS -----------------------
from routes.auth import auth_bp
from routes.onboarding import onboarding_bp
from routes.sahayak import sahayak_bp
from routes.subsidies import subsidies_bp
from routes.admin import admin_bp
from routes.admin_auth import admin_auth_bp
from routes.admin_store import admin_store_bp
from routes.admin_schemes import admin_schemes_bp
from routes.admin_notifications import admin_notifications_bp
from routes.admin_farmers import admin_farmers_bp
from routes.notifications import notifications_bp
from routes.crop_economics import crop_economics_bp
from routes.profit_simulator import profit_bp
from routes.field_monitoring import iot
from routes.bidding import bidding_bp
app.register_blueprint(iot)



from routes.weather import weather_bp
from routes.redemption_store import redemption_bp
from routes.buyer_auth import buyer_auth_bp

app.register_blueprint(auth_bp)
app.register_blueprint(onboarding_bp)
app.register_blueprint(sahayak_bp)
app.register_blueprint(subsidies_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(admin_auth_bp)
app.register_blueprint(admin_store_bp)
app.register_blueprint(admin_schemes_bp)
app.register_blueprint(admin_notifications_bp)
app.register_blueprint(admin_farmers_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(crop_economics_bp)   
app.register_blueprint(profit_bp)
app.register_blueprint(bidding_bp)


app.register_blueprint(weather_bp)
app.register_blueprint(redemption_bp)
app.register_blueprint(buyer_auth_bp)

# ----------------------- DATABASE INITIALIZATION ENDPOINT -----------------------
@app.route('/api/init-db', methods=['POST'])
def init_db_endpoint():
    """Endpoint to manually initialize database tables"""
    try:
        print("[DB INIT API] Initializing database tables...")
        db.create_all()
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"[DB INIT API] ✓ Created {len(tables)} tables")
        return {
            'status': 'success',
            'message': f'Database initialized with {len(tables)} tables',
            'tables': tables
        }, 200
    except Exception as e:
        print(f"[DB INIT API] ✗ Error: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }, 500

# ----------------------- SOCKET.IO EVENT HANDLERS -----------------------
# Register Socket.IO event handlers
from routes.socketio_events import register_socketio_events
register_socketio_events(socketio)

# Global SocketIO error handler
@socketio.on_error_default
def default_error_handler(e):
    """Handle any unhandled errors in Socket.IO"""
    print(f"[SOCKETIO ERROR] Unhandled error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()

# ----------------------- ROOT-LEVEL ESP32 ENDPOINTS -----------------------
# Import the handler function from field_monitoring
from routes.field_monitoring import handle_esp32_update

@app.route("/api/update", methods=["POST"])
@app.route("/api/push", methods=["POST"])
def root_esp32_update():
    """Root-level endpoints for ESP32 compatibility (bypasses blueprint prefix)"""
    return handle_esp32_update(request.json)

# ----------------------- ROUTES -----------------------

@app.route('/')
def home():
    """If authenticated → go to dashboard, else → login."""
    if 'farmer_id_verified' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth.login'))


@app.route('/index')
def index():
    """Redirect to login."""
    return redirect(url_for('auth.login'))


@app.route('/dashboard')
def dashboard():
    """Basic placeholder dashboard."""
    if 'farmer_id_verified' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html')


@app.route('/ping')
def ping():
    """Health check endpoint to prevent Render app from sleeping."""
    return {'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}, 200


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('static', filename)

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}


@app.before_request
def set_language_context():
    """Set language context before each request (static English only)"""
    g.language = 'en'


# ----------------------- APP RUN -----------------------
# Start the background scheduler when the app initializes
start_scheduler()

if __name__ == '__main__':
    # ❗️IMPORTANT: Do NOT use db.create_all() when using Flask-Migrate
    # Migrations now handle schema updates.
    
    # ❗️IMPORTANT: Use socketio.run() instead of app.run() for Socket.IO support
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)

