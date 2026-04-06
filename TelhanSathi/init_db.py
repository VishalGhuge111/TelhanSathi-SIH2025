#!/usr/bin/env python3
"""
Database initialization script - Utility for manual database initialization
The app now auto-initializes on startup, but this can be used for manual resets
"""
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def init_db():
    """Initialize database - create all tables"""
    try:
        from app import app, db
        
        with app.app_context():
            print("[DB INIT] ========================================")
            print("[DB INIT] Starting database initialization...")
            db_url = os.getenv('DATABASE_URL', 'sqlite:///telhan_sathi.db')
            print(f"[DB INIT] DATABASE_URL: {db_url[:60]}...")
            print(f"[DB INIT] Using SQLAlchemy URI: {app.config['SQLALCHEMY_DATABASE_URI'][:60]}...")
            
            # Create all tables
            print("[DB INIT] Creating database tables...")
            db.create_all()
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"[DB INIT] ✓ Created {len(tables)} tables: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}")
            print("[DB INIT] ✓ Database initialized successfully!")
            print("[DB INIT] ========================================")
            return True
            
    except Exception as e:
        print(f"[DB INIT] ✗ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        print("[DB INIT] Traceback:")
        traceback.print_exc()
        print("[DB INIT] ========================================")
        return False

if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1)

