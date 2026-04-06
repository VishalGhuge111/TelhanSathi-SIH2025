import random
import string
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

def generate_otp(length=6):
    """Generate a random OTP."""
    return ''.join(random.choices(string.digits, k=length))


def send_otp_sms(phone_number, otp_code):
    """
    Send OTP via SMS using Twilio.
    For development, just log it. For production, use actual Twilio.
    """
    # Development Mode: Print OTP
    env = os.getenv('FLASK_ENV', 'production')
    if env == 'development':
        print(f"[DEV MODE] OTP for {phone_number}: {otp_code}")
        return True

    # Production Mode: Use Twilio but validate credentials first
    try:
        from twilio.rest import Client

        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')

        missing = [name for name, val in (
            ('TWILIO_ACCOUNT_SID', account_sid),
            ('TWILIO_AUTH_TOKEN', auth_token),
            ('TWILIO_PHONE_NUMBER', twilio_phone),
        ) if not val]

        if missing:
            print(f"Twilio credentials missing: {', '.join(missing)}")
            # If local fallback is allowed (or not explicitly production), print OTP instead
            local_fallback = os.getenv('LOCAL_FALLBACK', 'true').lower() in ('1', 'true', 'yes')
            if local_fallback or env != 'production':
                print(f"[FALLBACK] OTP for {phone_number}: {otp_code}")
                return True
            return False

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=f"Your Telhan Sathi OTP is: {otp_code}. Valid for 5 minutes.",
            from_=twilio_phone,
            to=f"+91{phone_number}"
        )
        print(f"OTP sent via Twilio. Message SID: {message.sid}")
        return True
    except Exception as e:
        print(f"Error sending OTP via Twilio: {e}")
        # Fallback: Print OTP to logs for testing
        print(f"[FALLBACK - OTP PRINTED TO LOGS] OTP for {phone_number}: {otp_code}")
        print(f"[FALLBACK - OTP PRINTED TO LOGS] Valid for 5 minutes")
        return True  # Return True to allow testing even if Twilio fails


def calculate_otp_expiry():
    """Calculate OTP expiry time (5 minutes from now)."""
    expiry_seconds = int(os.getenv('OTP_EXPIRY_SECONDS', 300))
    return datetime.utcnow() + timedelta(seconds=expiry_seconds)


def is_farmer_eligible_for_subsidy(farmer):
    """
    Check if farmer is eligible for NMEO-OS subsidy.
    Rules: District must be in oilseed focus list, crop must be oilseed.
    """
    oilseed_focus_districts = {
        'Rajasthan': ['Bharatpur', 'Dausa', 'Jaipur', 'Pali', 'Jodhpur'],
        'Madhya Pradesh': ['Indore', 'Ujjain', 'Ratlam', 'Mandsaur'],
        'Gujarat': ['Kutch', 'Junagadh', 'Saurashtra'],
        'Odisha': ['Balangir', 'Nuapada', 'Kalahandi'],
    }
    
    oilseeds = ['Mustard', 'Groundnut', 'Soybean', 'Sunflower', 'Safflower']
    
    # Check district eligibility
    eligible_districts = oilseed_focus_districts.get(farmer.state, [])
    if farmer.district not in eligible_districts:
        return False
    
    # Check if switching to oilseed
    if farmer.current_crop and farmer.current_crop not in oilseeds:
        return True
    
    return False


def calculate_subsidy_amount(land_size_hectares, crop):
    """
    Calculate subsidy amount based on land size and crop type.
    NMEO-OS typical rates: ₹5000-7000 per hectare for seeds, ₹2000-3000 for inputs.
    """
    subsidy_rates = {
        'Mustard': 6000,      # ₹/hectare
        'Groundnut': 6500,
        'Soybean': 5500,
        'Sunflower': 5000,
        'Safflower': 4500,
    }
    
    rate_per_hectare = subsidy_rates.get(crop, 5000)
    return land_size_hectares * rate_per_hectare
