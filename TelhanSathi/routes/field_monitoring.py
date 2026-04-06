from flask import Blueprint, request, jsonify, render_template
import json
import os
from datetime import datetime

iot = Blueprint("iot", __name__, url_prefix="/field-monitoring")

DB_FILE = "database.json"
from flask import Response
import time
import json

@iot.route('/device-guide')
def device_guide():
    return render_template("iot_device_guide.html")

@iot.route('/device-control')
def device_control():
    return render_template("field_monitoring.html")

@iot.route("/api/stream")
def stream():
    def event_stream():
        last_data = None
        while True:
            db = load_db()
            current = json.dumps(db["current"])

            # Send update only if data changed
            if current != last_data:
                last_data = current
                yield f"data: {current}\n\n"

            time.sleep(1)

    return Response(event_stream(), mimetype="text/event-stream")

# -------------------------------
# Helper Functions
# -------------------------------

def load_db():
    """Load JSON database or create a new one."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {"current": {}, "history": []}
    return {"current": {}, "history": []}


def save_db(data):
    """Save data back to the JSON file with max 100 history entries."""
    if len(data["history"]) > 100:
        data["history"] = data["history"][-100:]

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)


def handle_esp32_update(raw):
    """Shared handler for ESP32 updates"""
    if not raw:
        return jsonify({"error": "No data received"}), 400

    now = datetime.now()
    
    # ==================== DEBUG: SHOW RAW PAYLOAD ====================
    print(f"\n{'='*60}")
    print(f"📨 RAW ESP32 PAYLOAD RECEIVED")
    print(f"{'='*60}")
    print(json.dumps(raw, indent=2))
    print(f"{'='*60}\n")

    # Build clean sensor dataset
    new_data = {
        "airTemp": float(raw.get("airTemp", 0)),
        "airHum": float(raw.get("airHum", 0)),
        "heatIndex": float(raw.get("heatIndex", 0)),
        "soilTemp": float(raw.get("soilTemp", 0)),
        "soilMoist": int(raw.get("soilMoist", 0)),
        "soilRaw": int(raw.get("soilRaw", 0)),
        "light": float(raw.get("light", 0)),
        "lightRaw": int(raw.get("lightRaw", 0)),
        "rssi": int(raw.get("rssi", 0)),
        "uptime": int(raw.get("uptime", 0)),
        "timestamp": now.strftime("%H:%M:%S"),
        "fullDate": now.isoformat()
    }

    db = load_db()
    db["current"] = new_data
    db["history"].append(new_data)

    save_db(db)
    
    # Log the update
    print(f"\n✓ ESP32 DATA RECEIVED & PROCESSED")
    print(f"  Temp: {new_data['airTemp']}°C, Humidity: {new_data['airHum']}%")
    print(f"  Soil: {new_data['soilMoist']}%, Light: {new_data['light']} lux")
    print(f"  RSSI: {new_data['rssi']} dBm, Uptime: {new_data['uptime']}s")
    print(f"  Time: {new_data['timestamp']}")
    print()

    return jsonify({"status": "success", "timestamp": new_data["fullDate"]})


# -------------------------------
# API ENDPOINTS
# -------------------------------

# 1. ESP32 sends data here (accepts both paths for flexibility)
@iot.route("/api/update", methods=["POST"])
@iot.route("/api/push", methods=["POST"])
def api_update():
    return handle_esp32_update(request.json)


# 2. Dashboard fetches data
@iot.route("/api/data", methods=["GET"])
def api_data():
    db = load_db()
    return jsonify(db)


# 3. RESET all logs (clear history)
@iot.route("/api/reset", methods=["POST"])
def api_reset():
    empty = {"current": {}, "history": []}
    save_db(empty)
    return jsonify({"status": "cleared"})
