from extensions import db
from datetime import datetime
import uuid

class Farmer(db.Model):
    """
    Farmer model based on Maharashtra AgriStack and MahaDBT portal schema.
    Stores comprehensive farmer profile including personal, address, land, and financial details.
    """
    __tablename__ = 'farmers'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # ===== PERSONAL & DEMOGRAPHIC INFORMATION =====
    # Kisan Pehchan Patra (12-digit ID) - Unique identifier
    farmer_id = db.Column(db.String(12), unique=True, nullable=False, index=True)
    
    # Name
    name = db.Column(db.String(255), nullable=False)
    
    # Date of Birth
    date_of_birth = db.Column(db.Date)
    
    # Gender (M/F/Other)
    gender = db.Column(db.String(10))
    
    # Contact Information
    phone_number = db.Column(db.String(10), nullable=False, unique=True, index=True)
    
    # Caste Category (General/OBC/SC/ST)
    caste_category = db.Column(db.String(50))
    
    # Physically Handicapped Status (Yes/No)
    is_physically_handicapped = db.Column(db.Boolean, default=False)
    
    # ===== ADDRESS INFORMATION =====
    # Permanent Address
    permanent_address = db.Column(db.String(500))
    
    # Location Details
    district = db.Column(db.String(100), nullable=False)
    taluka = db.Column(db.String(100))
    village = db.Column(db.String(100))
    state = db.Column(db.String(100), default='Maharashtra')
    
    pincode = db.Column(db.String(6))
    
    # GPS Coordinates (for location-based services)
    
    # ===== LAND OWNERSHIP & AGRICULTURAL DETAILS =====
    # Total Land Area in hectares
    total_land_area_hectares = db.Column(db.Float, nullable=False, default=0.0)
    
    # Land Area in Gunthas (traditional Maharashtrian measurement: 1 guntha ≈ 0.025 hectare)
    land_area_gunthas = db.Column(db.Float, default=0.0)
    
    # Land Holder Type (Owner/Co-owner/Tenant/Sharecropper)
    land_holder_type = db.Column(db.String(50), default='Owner')
    
    # Soil Type (Loamy, Clay, Sandy, Black Soil, Red Soil, etc.)
    soil_type = db.Column(db.String(100))
    
    # Current Crop(s) cultivated (stored as comma-separated or JSON)
    current_crops = db.Column(db.String(500))
    
    # Oilseed Farmer Status (enrolled in oilseed cultivation scheme)
    is_oilseed_farmer = db.Column(db.Boolean, default=False)
    oilseed_enrollment_date = db.Column(db.DateTime)
    
    # ===== FINANCIAL INFORMATION =====
    # Income Information
    annual_income = db.Column(db.Float)
    
    # PM-KISAN Beneficiary Status
    is_pm_kisan_beneficiary = db.Column(db.Boolean, default=False)
    pm_kisan_reference_id = db.Column(db.String(100))
    
    # ===== ACCOUNT STATUS & VERIFICATION =====
    is_verified = db.Column(db.Boolean, default=False)
    verification_timestamp = db.Column(db.DateTime)

    # Has the farmer completed the onboarding flow?
    onboarding_completed = db.Column(db.Boolean, default=False)
    
    # Water Type (Freshwater, Salt Water, Brackish Water)
    water_type = db.Column(db.String(50))

    # Harvest Date (YYYY-MM)
    harvest_date = db.Column(db.Date)

    # Selected unit for land size (acre / hectare / bigha)
    land_unit = db.Column(db.String(20), default="acre")

    # Current Crop(s) cultivated (stored as comma-separated or JSON)
    current_crops = db.Column(db.String(500))
    
    # ===== GAMIFICATION =====
    coins_earned = db.Column(db.Integer, default=0)  # Total coins earned
    
    # Profile Picture (stores filename)
    profile_pic = db.Column(db.String(255), default=None)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ===== RELATIONSHIPS =====
    otp_records = db.relationship('OTPRecord', backref='farmer', lazy=True, cascade='all, delete-orphan')
    subsidy_applications = db.relationship('SubsidyApplication', backref='farmer', lazy=True, cascade='all, delete-orphan')
    price_alerts = db.relationship('PriceAlert', backref='farmer', lazy=True, cascade='all, delete-orphan')
    rewards = db.relationship('FarmerReward', backref='farmer', lazy=True, cascade='all, delete-orphan')
    coin_balance = db.relationship('CoinBalance', backref='farmer', uselist=False, cascade='all, delete-orphan')


    
    def __repr__(self):
        return f'<Farmer {self.farmer_id} - {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'name': self.name,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'phone_number': self.phone_number,
            'caste_category': self.caste_category,
            'is_physically_handicapped': self.is_physically_handicapped,
            'permanent_address': self.permanent_address,
            'district': self.district,
            'taluka': self.taluka,
            'village': self.village,
            'state': self.state,
            'pincode': self.pincode,
            'total_land_area_hectares': self.total_land_area_hectares,
            'land_area_gunthas': self.land_area_gunthas,
            'land_holder_type': self.land_holder_type,
            'land_unit': self.land_unit,
            'soil_type': self.soil_type,
            'water_type': self.water_type,
            'current_crops': self.current_crops,
            'harvest_date': self.harvest_date.isoformat() if self.harvest_date else None,
            'is_oilseed_farmer': self.is_oilseed_farmer,
            'annual_income': self.annual_income,
            'is_pm_kisan_beneficiary': self.is_pm_kisan_beneficiary,
            'coins_earned': self.coins_earned,
            'profile_pic': self.profile_pic,
            'is_verified': self.is_verified,
        }



class OTPRecord(db.Model):
    """
    OTP authentication records for Farmer ID-based login.
    Stores OTP, expiry, and verification status.
    """
    __tablename__ = 'otp_records'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False)
    
    otp_code = db.Column(db.String(6), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified_at = db.Column(db.DateTime)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f'<OTP {self.otp_code} for Farmer {self.farmer_id}>'


class Scheme(db.Model):
    r"""
    Master list of government schemes and subsidies.
        cd "C:\Users\dhira\OneDrive\Desktop\dhirudurgade github\TelhanSathi-SIH2025\backend"
    flask db migrate -m "Add Scheme and SubsidyApplication models"
    flask db upgrades all available subsidies/schemes data.
    """
    __tablename__ = 'schemes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Scheme Identifier
    scheme_code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g., 'pmkisan', 'nmeo'
    
    # Basic Information
    name = db.Column(db.String(255), nullable=False)  # PM-KISAN Samman Nidhi
    description = db.Column(db.Text, nullable=False)  # Full description
    
    # Category/Type
    scheme_type = db.Column(db.String(50), nullable=False)  # 'subsidy' or 'scheme'
    focus_area = db.Column(db.String(100), nullable=False)  # Income Support, Crop Switch, Equipment, etc.
    focus_color = db.Column(db.String(20), default="#2196f3")  # Color code for UI
    
    # Benefit Details
    benefit_amount = db.Column(db.String(255), nullable=False)  # ₹6,000/year, 40-50% Subsidy, etc.
    eligibility_criteria = db.Column(db.Text, nullable=False)  # Eligibility requirements
    
    # How to Apply (stored as JSON list of steps)
    apply_steps = db.Column(db.Text)  # JSON array of application steps
    
    # External Link for more info or direct application
    external_link = db.Column(db.String(255))
    
    # Recommendation Flag (for "Recommended for You" filter)
    is_recommended = db.Column(db.Boolean, default=False)
    
    # Active Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Required Documents (stored as JSON list)
    required_documents = db.Column(db.Text)  # JSON array of required documents
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subsidy_applications = db.relationship('SubsidyApplication', backref='scheme', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Scheme {self.name}>'
    
    def to_dict(self):
        """Convert scheme to dictionary for JSON response."""
        import json
        return {
            'id': self.id,
            'scheme_code': self.scheme_code,
            'name': self.name,
            'description': self.description,
            'scheme_type': self.scheme_type,
            'focus_area': self.focus_area,
            'focus_color': self.focus_color,
            'benefit_amount': self.benefit_amount,
            'eligibility_criteria': self.eligibility_criteria,
            'apply_steps': json.loads(self.apply_steps) if self.apply_steps else [],
            'external_link': self.external_link,
            'is_recommended': self.is_recommended,
            'is_active': self.is_active,
            'required_documents': json.loads(self.required_documents) if self.required_documents else [],
            'created_at': self.created_at.isoformat()
        }


class SubsidyApplication(db.Model):
    """
    Tracks farmer applications for specific schemes/subsidies.
    """
    __tablename__ = 'subsidy_applications'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False)
    scheme_id = db.Column(db.String(36), db.ForeignKey('schemes.id'), nullable=False)
    
    # Application Details
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Status: Applied, Verified, Approved, Disbursed, Rejected
    status = db.Column(db.String(50), default='Applied')
    
    # Subsidy/Scheme Specific Data (JSON for flexibility)
    application_data = db.Column(db.Text)  # JSON: crop, quantity, location, etc.
    
    # Approval Details
    approved_amount = db.Column(db.Float)
    approval_date = db.Column(db.DateTime)
    
    # Generated PDF path (auto-filled application)
    application_pdf_path = db.Column(db.String(255))
    
    # Notes from admin
    admin_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SubsidyApplication {self.scheme_id} - {self.status}>'


class PriceAlert(db.Model):
    """
    Price alerts for oilseed commodities.
    Stores alert preferences and notification history.
    """
    __tablename__ = 'price_alerts'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False)
    
    # Commodity: Mustard, Groundnut, Soybean, etc.
    commodity = db.Column(db.String(100), nullable=False)
    
    # Target Market/Mandi
    mandi_name = db.Column(db.String(100))
    
    # Alert Threshold (price in ₹/quintal)
    alert_price = db.Column(db.Float, nullable=False)
    alert_type = db.Column(db.String(20))  # 'above' or 'below'
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PriceAlert {self.commodity} @ {self.mandi_name}>'


class FarmerReward(db.Model):
    """
    Gamification - Rewards and points system.
    """
    __tablename__ = 'farmer_rewards'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False)
    
    total_points = db.Column(db.Float, default=0)
    
    # Point breakdown
    points_from_switching = db.Column(db.Float, default=0)  # 500 pts
    points_from_soil_test = db.Column(db.Float, default=0)  # 100 pts
    points_from_sales = db.Column(db.Float, default=0)  # 200 pts
    
    rank = db.Column(db.Integer)  # Village/District leaderboard rank
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FarmerReward Points: {self.total_points}>'


class Notification(db.Model):
    r"""
    Notifications for farmers - alerts, updates, important messages.
    Types: scheme_update, deal_alert, price_alert, general_alert, system_update
    """
    __tablename__ = 'notifications'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # scheme_update, deal_alert, price_alert, general_alert, system_update
    icon = db.Column(db.String(50), nullable=True)  # Icon name for frontend display
    color = db.Column(db.String(20), nullable=True)  # Color code (success, warning, info, error)
    related_id = db.Column(db.String(36), nullable=True)  # Links to scheme/deal/crop if applicable
    related_type = db.Column(db.String(50), nullable=True)  # scheme, deal, crop, general
    action_link = db.Column(db.String(255), nullable=True)  # URL to navigate to
    is_read = db.Column(db.Boolean, default=False)
    is_important = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=True)  # Auto-expire old notifications
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.title} for Farmer {self.farmer_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.notification_type,
            'icon': self.icon,
            'color': self.color,
            'relatedId': self.related_id,
            'relatedType': self.related_type,
            'actionLink': self.action_link,
            'isRead': self.is_read,
            'isImportant': self.is_important,
            'expiresAt': self.expires_at.isoformat() if self.expires_at else None,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }


class DeviceRequest(db.Model):
    """Records farmer requests for an IoT kit installation."""
    __tablename__ = 'device_requests'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False, index=True)
    
    # Request Details
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected, scheduled, installed
    priority = db.Column(db.String(20), default='normal')  # low, normal, high
    
    # Request Information
    land_area_hectares = db.Column(db.Float)  # Area to be monitored
    field_location = db.Column(db.String(255))  # GPS or description
    preferred_installation_date = db.Column(db.Date)
    
    # Notes and Comments
    farmer_notes = db.Column(db.Text)  # What farmer wants
    admin_notes = db.Column(db.Text)  # Internal notes
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheduled_date = db.Column(db.DateTime)  # When installation is scheduled
    completed_date = db.Column(db.DateTime)  # When installation was completed
    
    # Device Assignment
    assigned_device_id = db.Column(db.String(36), db.ForeignKey('iot_devices.id'))
    
    def __repr__(self):
        return f'<DeviceRequest {self.id} farmer:{self.farmer_id} status:{self.status}>'
    
    def to_dict(self):
        """Convert request to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'status': self.status,
            'priority': self.priority,
            'land_area_hectares': self.land_area_hectares,
            'field_location': self.field_location,
            'preferred_installation_date': self.preferred_installation_date.isoformat() if self.preferred_installation_date else None,
            'farmer_notes': self.farmer_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None
        }


class IoTDevice(db.Model):
    """Represents an installed IoT kit (ESP32 + sensors) for a farmer."""
    __tablename__ = 'iot_devices'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False, index=True)
    
    # Device Identification
    device_serial = db.Column(db.String(100), unique=True, index=True)
    device_mac = db.Column(db.String(20), unique=True)  # MAC address for device tracking
    device_name = db.Column(db.String(100))  # User-friendly device name
    
    # Installation Status
    installed = db.Column(db.Boolean, default=False)
    installed_at = db.Column(db.DateTime)
    location_description = db.Column(db.String(255))  # e.g., "North Field, near well"
    
    # Device Status
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime)  # Last time device sent data
    
    # Device Configuration
    wifi_ssid = db.Column(db.String(100))  # Connected WiFi network
    firmware_version = db.Column(db.String(50))  # ESP32 firmware version
    
    # Calibration Data
    soil_dry_value = db.Column(db.Integer)  # Raw ADC value for dry soil (for calibration)
    soil_wet_value = db.Column(db.Integer)  # Raw ADC value for wet soil (for calibration)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    readings = db.relationship('SensorReading', backref='device', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<IoTDevice {self.device_serial} farmer:{self.farmer_id}>'
    
    def to_dict(self):
        """Convert device to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'device_serial': self.device_serial,
            'device_mac': self.device_mac,
            'device_name': self.device_name,
            'installed': self.installed,
            'installed_at': self.installed_at.isoformat() if self.installed_at else None,
            'location_description': self.location_description,
            'is_active': self.is_active,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'wifi_ssid': self.wifi_ssid,
            'firmware_version': self.firmware_version,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SensorReading(db.Model):
    """Stores sensor readings pushed from the IoT kit."""
    __tablename__ = 'sensor_readings'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = db.Column(db.String(36), db.ForeignKey('iot_devices.id'), nullable=False)
    
    # Temperature & Humidity (DHT22)
    temperature = db.Column(db.Float)  # ambient air temperature (°C)
    humidity = db.Column(db.Float)  # air humidity (%)
    heat_index = db.Column(db.Float)  # heat index/feel-like temperature (°C)
    
    # Soil Sensors
    soil_moisture = db.Column(db.Float)  # soil moisture (%)
    soil_raw = db.Column(db.Integer)  # raw ADC value for soil sensor (0-4095)
    soil_temp = db.Column(db.Float)  # soil temperature from DS18B20 (°C)
    
    # Light Sensor (LDR)
    light = db.Column(db.Float)  # light intensity in lux
    light_raw = db.Column(db.Integer)  # raw ADC value for light sensor (0-4095)
    
    # Signal Strength
    rssi = db.Column(db.Integer)  # WiFi RSSI (signal strength in dBm)
    
    # Device Uptime
    uptime = db.Column(db.Integer)  # device uptime in seconds
    
    # Timestamp
    received_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<SensorReading {self.id} device:{self.device_id} at {self.received_at}>'
    
    def to_dict(self):
        """Convert reading to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'soil_moisture': self.soil_moisture,
            'soil_temp': self.soil_temp,
            'light': self.light,
            'light_raw': self.light_raw,
            'rssi': self.rssi,
            'uptime': self.uptime,
            'received_at': self.received_at.isoformat() if self.received_at else None
        }


# ===== GAMIFICATION & REDEMPTION MODELS =====

class CoinBalance(db.Model):
    """Tracks total coins earned by each farmer."""
    __tablename__ = 'coin_balances'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), unique=True, nullable=False)
    total_coins = db.Column(db.Integer, default=0)
    available_coins = db.Column(db.Integer, default=0)
    redeemed_coins = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('CoinTransaction', backref='coin_balance', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CoinBalance farmer:{self.farmer_id} available:{self.available_coins}>'


class CoinTransaction(db.Model):
    """Records all coin earnings and redemptions."""
    __tablename__ = 'coin_transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    coin_balance_id = db.Column(db.String(36), db.ForeignKey('coin_balances.id'), nullable=False)
    
    transaction_type = db.Column(db.String(50), nullable=False)  # earned, redeemed
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))  # e.g., "Subsidy Applied", "Deal Completed", etc.
    
    related_type = db.Column(db.String(50))  # subsidy_application, marketplace_deal, etc.
    related_id = db.Column(db.String(36))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CoinTransaction {self.transaction_type} {self.amount} coins>'


class RedemptionOffer(db.Model):
    """Catalog of all redemption offers available in the store."""
    __tablename__ = 'redemption_offers'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Offer details
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Farm Inputs, Services, Yantra, Tech, VIP
    
    coin_cost = db.Column(db.Integer, nullable=False)
    icon = db.Column(db.String(50))  # Emoji or icon identifier
    color = db.Column(db.String(7), default='#388e3c')  # Hex color
    
    # Offer metadata
    offer_type = db.Column(db.String(50))  # discount, free, service, etc.
    actual_value = db.Column(db.String(255))  # e.g., "₹500", "Free", "30 Days"
    validity_days = db.Column(db.Integer, default=90)
    
    # Availability
    is_active = db.Column(db.Boolean, default=True)
    stock_limit = db.Column(db.Integer)  # None = unlimited
    stock_redeemed = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    redemptions = db.relationship('FarmerRedemption', backref='offer', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<RedemptionOffer {self.title} - {self.coin_cost} coins>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'coin_cost': self.coin_cost,
            'icon': self.icon,
            'color': self.color,
            'offer_type': self.offer_type,
            'actual_value': self.actual_value,
            'validity_days': self.validity_days,
            'is_active': self.is_active,
            'stock_limit': self.stock_limit,
            'stock_redeemed': self.stock_redeemed,
            'available_stock': self.stock_limit - self.stock_redeemed if self.stock_limit else None
        }


class FarmerRedemption(db.Model):
    """Records individual farmer redemptions."""
    __tablename__ = 'farmer_redemptions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False)
    offer_id = db.Column(db.String(36), db.ForeignKey('redemption_offers.id'), nullable=False)
    
    # Redemption details
    coins_spent = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='active')  # active, expired, used, cancelled
    
    redeemed_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Calculated from validity_days
    used_at = db.Column(db.DateTime)
    
    # Code for redemption (e.g., coupon code, reference ID)
    redemption_code = db.Column(db.String(50), unique=True)
    
    # Additional metadata
    notes = db.Column(db.Text)  # Usage notes, status updates
    
    farmer = db.relationship('Farmer', backref='redemptions')
    
    def __repr__(self):
        return f'<FarmerRedemption {self.redemption_code} status:{self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'offer_title': self.offer.title,
            'offer_id': self.offer_id,
            'coins_spent': self.coins_spent,
            'status': self.status,
            'redeemed_at': self.redeemed_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'redemption_code': self.redemption_code
        }


class FarmerRecommendation(db.Model):
    """
    Stores AI-generated scheme recommendations for farmers.
    Prevents repeated API calls by caching recommendations in database.
    """
    __tablename__ = 'farmer_recommendations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False, index=True)
    scheme_id = db.Column(db.String(36), db.ForeignKey('schemes.id'), nullable=False)
    
    # Recommendation details
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    match_percentage = db.Column(db.Integer, default=0)  # 0-100
    reason = db.Column(db.Text)  # Why this scheme is recommended
    
    # AI method used
    ai_method = db.Column(db.String(50), default='gemini')  # gemini, rule_based, hybrid
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime)  # Recommendation expires after 24 hours
    
    # Relationships
    farmer = db.relationship('Farmer', backref='recommendations', lazy=True)
    scheme = db.relationship('Scheme', backref='recommended_for', lazy=True)
    
    def __repr__(self):
        return f'<FarmerRecommendation {self.farmer_id}-{self.scheme_id} {self.priority}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'scheme_id': self.scheme_id,
            'scheme_name': self.scheme.name if self.scheme else 'Unknown',
            'description': self.scheme.description if self.scheme else '',
            'benefit_amount': self.scheme.benefit_amount if self.scheme else '',
            'eligibility_criteria': self.scheme.eligibility_criteria if self.scheme else '',
            'focus_area': self.scheme.focus_area if self.scheme else '',
            'focus_color': self.scheme.focus_color if self.scheme else '#2196f3',
            'external_link': self.scheme.external_link if self.scheme else '',
            'priority': self.priority,
            'match_percentage': self.match_percentage,
            'reason': self.reason,
            'ai_method': self.ai_method,
            'created_at': self.created_at.isoformat()
        }


class WeatherRecommendation(db.Model):
    """
    Stores AI-generated weather-based recommendations for farmers.
    Provides crop-specific advice on irrigation, fertilizer, pest control, and weather alerts.
    Prevents repeated Gemini API calls by caching recommendations in database.
    """
    __tablename__ = 'weather_recommendations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False, index=True)
    
    # Weather data snapshot when recommendation was generated
    weather_data = db.Column(db.JSON)  # 7-day forecast data
    
    # AI-generated recommendations in structured format
    recommendations = db.Column(db.JSON)  # {irrigation_advice, pest_alerts, fertilizer_timing, weather_warnings, seasonal_insights}
    
    # Chat context for follow-up questions (stores conversation history)
    chat_context = db.Column(db.JSON, default=None)  # [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    
    # AI method used
    ai_method = db.Column(db.String(50), default='gemini')  # gemini, rule_based
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime)  # Recommendation expires after 24 hours
    last_refreshed_at = db.Column(db.DateTime, default=datetime.utcnow)  # Track when recommendation was last refreshed
    
    # Relationships
    farmer = db.relationship('Farmer', backref='weather_recommendations', lazy=True)
    
    def __repr__(self):
        return f'<WeatherRecommendation {self.farmer_id} created_at={self.created_at}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'farmer_id': self.farmer_id,
            'weather_data': self.weather_data,
            'recommendations': self.recommendations,
            'chat_context': self.chat_context,
            'ai_method': self.ai_method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_refreshed_at': self.last_refreshed_at.isoformat() if self.last_refreshed_at else None,
            'is_valid': self.expires_at > datetime.utcnow() if self.expires_at else False
        }


class Admin(db.Model):
    """
    Admin user model for TelhanSathi platform administration.
    Stores admin credentials and profile information.
    """
    __tablename__ = 'admins'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Admin Credentials
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Admin Profile
    full_name = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(15))
    
    # Role and Permissions
    role = db.Column(db.String(50), default='admin')  # admin, super_admin, moderator
    department = db.Column(db.String(100))  # e.g., Finance, Support, Analytics
    
    # Account Status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Admin {self.email} - {self.role}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'phone_number': self.phone_number,
            'role': self.role,
            'department': self.department,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

