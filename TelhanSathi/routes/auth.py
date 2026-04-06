from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from datetime import datetime
from functools import wraps
import sys
import os
from werkzeug.utils import secure_filename
import secrets

# Avoid circular imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Farmer, OTPRecord, CoinBalance, Notification
from extensions import db
from utils import generate_otp, send_otp_sms, calculate_otp_expiry, is_farmer_eligible_for_subsidy
from models_marketplace_keep import Chat, ChatMessage

# Profile picture upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', 'profile_pics')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_profile_pic(file, farmer_id):
    """Save profile picture and return filename"""
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        return None
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return None
    
    # Generate unique filename
    ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    filename = f"farmer_{farmer_id}_{secrets.token_hex(8)}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    return filename

auth_bp = Blueprint('auth', __name__)

# ===== AUTHENTICATION DECORATOR =====
def login_required(f):
    """Decorator to check if user is logged in (OTP verified)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if farmer_id_verified exists in session (means OTP was verified)
        if 'farmer_id_verified' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# ===== LOGIN FLOW ROUTES (Jinja2 Templating) =====

@auth_bp.route('/login', methods=['GET'])
def login():
    """Serve login page"""
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login_with_mobile():
    """Handle login with mobile number - creates new farmer if needed"""
    import re
    import random
    import string
    
    mobile_number = request.form.get('mobile_number', '').strip()
    
    if not mobile_number:
        return render_template('login.html', error='Please enter your mobile number')
    
    # Validate mobile number format (Indian: 10 digits, optionally with +91 prefix)
    mobile_pattern = r'^(\+91)?[6-9]\d{9}$'
    if not re.match(mobile_pattern, mobile_number):
        return render_template('login.html', error='Please enter a valid 10-digit mobile number')
    
    # Normalize mobile number (remove +91 if present, keep only 10 digits)
    mobile_number = mobile_number.lstrip('+91').lstrip('0')
    if len(mobile_number) != 10:
        mobile_number = mobile_number[-10:]  # Take last 10 digits
    
    # Try to find farmer with this phone number
    farmer = Farmer.query.filter_by(phone_number=mobile_number).first()
    
    # If farmer doesn't exist, create new one
    if not farmer:
        try:
            # Generate unique farmer_id (12-digit format: MMMXXXXXXXX where MMM=Maharashtra code 100, XXXXXXXX=random)
            def generate_farmer_id():
                # Maharashtra code + 8 random digits
                while True:
                    farmer_id = '100' + ''.join([str(random.randint(0, 9)) for _ in range(9)])
                    # Check if this ID already exists
                    if not Farmer.query.filter_by(farmer_id=farmer_id).first():
                        return farmer_id
            
            # Create new farmer with minimal data
            farmer = Farmer(
                farmer_id=generate_farmer_id(),
                phone_number=mobile_number,
                name='',  # Will be filled during onboarding
                district='',  # Will be updated in onboarding
                onboarding_completed=False,
                is_verified=True,  # Mark as verified since they'll complete onboarding
                coins_earned=0  # Initialize coins to 0
            )
            db.session.add(farmer)
            db.session.flush()  # Flush to get the farmer.id before committing
            
            # Create CoinBalance with 500 welcome coins for demo app
            coin_balance = CoinBalance(
                farmer_id=farmer.id,
                total_coins=500,
                available_coins=500,  # 500 coins as welcome bonus
                redeemed_coins=0
            )
            db.session.add(coin_balance)
            
            # Create welcome notification
            welcome_notif = Notification(
                farmer_id=farmer.id,
                title='टेलहन साथी में आपका स्वागत है! 🎉',
                description='आपने सफलतापूर्वक पंजीकरण कर लिया है। आपको 500 स्वागत सिक्के मिले हैं! इन सिक्कों का उपयोग रिडेम्पशन स्टोर में कर सकते हैं।',
                notification_type='system_update',
                icon='celebration',
                color='success',
                related_type='general',
                is_important=True
            )
            db.session.add(welcome_notif)
            
            # Create scheme notification
            scheme_notif = Notification(
                farmer_id=farmer.id,
                title='सरकारी योजनाएं खोजें',
                description='आप अब सभी सरकारी योजनाओं और सब्सिडी के लिए आवेदन कर सकते हैं। अपनी खेत की जानकारी पूरी करें और सर्वोत्तम योजनाएं पाएं।',
                notification_type='scheme_update',
                icon='policy',
                color='info',
                related_type='general',
                action_link='/subsidies'
            )
            db.session.add(scheme_notif)
            
            # Create feature notification
            feature_notif = Notification(
                farmer_id=farmer.id,
                title='डिजिटल मंडी - नीलामी शुरू करें',
                description='अपनी फसल को सीधे खरीदारों को बेचें और बेहतर कीमत पाएं। अभी खेत के विवरण जोड़ें और नीलामी शुरू करें।',
                notification_type='deal_alert',
                icon='storefront',
                color='success',
                related_type='general',
                action_link='/auction'
            )
            db.session.add(feature_notif)
            
            db.session.commit()
            
            # Mark as new farmer
            session['new_farmer'] = True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating farmer: {str(e)}")  # Log the error for debugging
            return render_template('login.html', error='Error creating farmer profile. Please try again.')
    else:
        # Mark as existing farmer
        session['new_farmer'] = False
    
    # Generate and send OTP
    otp_code = generate_otp()
    otp_record = OTPRecord(
        farmer_id=farmer.id,
        otp_code=otp_code,
        expires_at=calculate_otp_expiry()
    )
    
    db.session.add(otp_record)
    db.session.commit()
    
    # Send OTP
    send_otp_sms(mobile_number, otp_code)
    
    # Store in session
    session['farmer_id'] = farmer.farmer_id
    session['phone_number'] = mobile_number
    session['login_method'] = 'mobile'
    session['internal_farmer_id'] = farmer.id  # Store internal ID for queries
    
    # Redirect to OTP verification page
    phone_masked = mobile_number[-4:]
    return render_template('otp.html', farmer_id=farmer.farmer_id, phone_masked=phone_masked, generated_otp=otp_code)


@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp_post():
    """Handle OTP verification"""
    farmer_id = request.form.get('farmer_id', '').strip()
    otp_code = request.form.get('otp_code', '').strip()
    
    if not farmer_id or not otp_code:
        phone_masked = session.get('phone_number', '')
        if phone_masked:
            phone_masked = phone_masked[-4:]
        # Get current OTP for demo display
        farmer = Farmer.query.filter_by(farmer_id=farmer_id).first()
        generated_otp = None
        if farmer:
            latest_otp = OTPRecord.query.filter_by(
                farmer_id=farmer.id,
                is_verified=False
            ).order_by(OTPRecord.created_at.desc()).first()
            if latest_otp:
                generated_otp = latest_otp.otp_code
        return render_template('otp.html', farmer_id=farmer_id, phone_masked=phone_masked, generated_otp=generated_otp, error='Invalid OTP input')
    
    # Find farmer
    farmer = Farmer.query.filter_by(farmer_id=farmer_id).first()
    if not farmer:
        phone_masked = session.get('phone_number', '')
        if phone_masked:
            phone_masked = phone_masked[-4:]
        return render_template('otp.html', farmer_id=farmer_id, phone_masked=phone_masked, error='Farmer not found')
    
    # Find latest OTP record
    otp_record = OTPRecord.query.filter_by(
        farmer_id=farmer.id,
        otp_code=otp_code,
        is_verified=False
    ).order_by(OTPRecord.created_at.desc()).first()
    
    if not otp_record:
        phone_masked = session.get('phone_number', '')
        if phone_masked:
            phone_masked = phone_masked[-4:]
        # Get current OTP for demo display
        latest_otp = OTPRecord.query.filter_by(
            farmer_id=farmer.id,
            is_verified=False
        ).order_by(OTPRecord.created_at.desc()).first()
        generated_otp = latest_otp.otp_code if latest_otp else None
        return render_template('otp.html', farmer_id=farmer_id, phone_masked=phone_masked, generated_otp=generated_otp, error='Invalid OTP')
    
    # Check expiry
    if otp_record.is_expired():
        phone_masked = session.get('phone_number', '')
        if phone_masked:
            phone_masked = phone_masked[-4:]
        return render_template('otp.html', farmer_id=farmer_id, phone_masked=phone_masked, generated_otp=otp_record.otp_code, error='OTP has expired')
    
    # Mark OTP as verified
    otp_record.is_verified = True
    otp_record.verified_at = datetime.utcnow()
    farmer.is_verified = True
    farmer.verification_timestamp = datetime.utcnow()
    
    db.session.commit()
    
    # Store farmer info in session
    session['farmer_id_verified'] = farmer.id
    session['farmer_kisan_id'] = farmer.farmer_id
    
    # If the farmer has completed onboarding previously, go to dashboard.
    # Otherwise route to unified onboarding to collect comprehensive profile information.
    try:
        if getattr(farmer, 'onboarding_completed', False):
            return redirect(url_for('dashboard'))
    except Exception:
        # If any issue accessing the flag, fall back to onboarding
        pass

    # Redirect to consolidated onboarding form
    return redirect(url_for('onboarding.onboarding'))


@auth_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    """Serve profile page after OTP verification (login required)"""
    farmer_id = session.get('farmer_id_verified')
    
    farmer = Farmer.query.filter_by(id=farmer_id).first()
    if not farmer:
        session.clear()
        return redirect(url_for('auth.login'))
    
    return render_template('profile.html', farmer=farmer.to_dict())



@auth_bp.route('/continue-to-dashboard', methods=['POST'])
@login_required
def continue_to_dashboard():
    """Handle continue button - routes based on farmer status"""
    farmer_id = session.get('farmer_id_verified')
    farmer = Farmer.query.filter_by(id=farmer_id).first()
    
    if not farmer:
        session.clear()
        return redirect(url_for('auth.login'))
    # Route to dashboard (Sahayak) for all users - bot will handle suggestions
    return redirect(url_for('dashboard'))


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend OTP via JSON API"""
    data = request.get_json()
    farmer_id = data.get('farmer_id', '').strip()
    
    farmer = Farmer.query.filter_by(farmer_id=farmer_id).first()
    if not farmer:
        return jsonify({'success': False, 'error': 'Farmer not found'}), 404
    
    # Generate and send new OTP
    otp_code = generate_otp()
    otp_record = OTPRecord(
        farmer_id=farmer.id,
        otp_code=otp_code,
        expires_at=calculate_otp_expiry()
    )
    
    db.session.add(otp_record)
    db.session.commit()
    
    send_otp_sms(farmer.phone_number, otp_code)
    
    return jsonify({'success': True, 'message': 'OTP resent successfully', 'generated_otp': otp_code}), 200


@auth_bp.route('/register', methods=['GET'])
def register():
    """Serve registration page (placeholder)"""
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    """Clear session and log the user out"""
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/me', methods=['GET'])
def api_current_farmer():
    """Return current logged-in farmer info as JSON (protected)"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    farmer_id = session.get('farmer_id_verified')
    farmer = Farmer.query.filter_by(id=farmer_id).first()
    if not farmer:
        return jsonify({'error': 'Farmer not found', 'status': 404}), 404
    return jsonify({
        'id': farmer.id,
        'name': farmer.name,
        'farmer_id': farmer.farmer_id,
        'phone_number': farmer.phone_number,
        'gender': farmer.gender,
        'date_of_birth': farmer.date_of_birth.isoformat() if farmer.date_of_birth else None,
        'caste_category': farmer.caste_category,
        'is_physically_handicapped': farmer.is_physically_handicapped,
        'permanent_address': farmer.permanent_address,
        'village': farmer.village,
        'taluka': farmer.taluka,
        'district': farmer.district,
        'state': farmer.state,
        'pincode': farmer.pincode,
        'total_land_area_hectares': farmer.total_land_area_hectares,
        'land_area_gunthas': farmer.land_area_gunthas,
        'land_holder_type': farmer.land_holder_type,
        'land_unit': farmer.land_unit,
        'soil_type': farmer.soil_type,
        'water_type': farmer.water_type,
        'current_crops': farmer.current_crops,
        'harvest_date': farmer.harvest_date,
        'is_oilseed_farmer': farmer.is_oilseed_farmer,
        'annual_income': farmer.annual_income,
        'is_pm_kisan_beneficiary': farmer.is_pm_kisan_beneficiary,
        'coins_earned': farmer.coins_earned,
        'is_verified': farmer.is_verified
    })


# ===== FARMER CHAT API =====

@auth_bp.route('/chats')
@login_required
def farmer_chats():
    """Render farmer chats page"""
    return render_template('farmer_chats.html')


@auth_bp.route('/api/farmer/chats', methods=['GET'])
def get_farmer_chats():
    """Get all chats for farmer"""
    try:
        farmer_id_verified = session.get('farmer_id_verified')
        if not farmer_id_verified:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Get all chats for this farmer
        chats = Chat.query.filter_by(farmer_id=farmer_id_verified, is_active=True).order_by(Chat.last_message_at.desc()).all()
        
        chats_data = []
        for chat in chats:
            # Get last message
            last_message = ChatMessage.query.filter_by(chat_id=chat.id).order_by(ChatMessage.created_at.desc()).first()
            
            chats_data.append({
                'id': chat.id,
                'buyer_id': chat.buyer_id,
                'crop_name': chat.crop_name,
                'sell_request_id': chat.sell_request_id,
                'buyer_offer_id': chat.buyer_offer_id,
                'is_active': chat.is_active,
                'created_at': chat.created_at.isoformat(),
                'last_message': {
                    'text': last_message.message if last_message else None,
                    'sender': last_message.sender_type if last_message else None,
                    'time': last_message.created_at.isoformat() if last_message else None
                },
                'message_count': len(chat.messages)
            })
        
        return jsonify(chats_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/farmer/chats/<chat_id>/messages', methods=['GET'])
def get_farmer_chat_messages(chat_id):
    """Get all messages in a chat for farmer"""
    try:
        farmer_id_verified = session.get('farmer_id_verified')
        if not farmer_id_verified:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Verify chat belongs to farmer
        chat = Chat.query.filter_by(id=chat_id, farmer_id=farmer_id_verified).first()
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Get all messages
        messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at.asc()).all()
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'sender_type': msg.sender_type,
                'sender_name': msg.sender_name,
                'message': msg.message,
                'created_at': msg.created_at.isoformat(),
                'is_read': msg.is_read
            })
        
        return jsonify(messages_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/farmer/chats/<chat_id>/messages', methods=['POST'])
def send_farmer_chat_message(chat_id):
    """Send a message in chat as farmer"""
    try:
        farmer_id_verified = session.get('farmer_id_verified')
        if not farmer_id_verified:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Verify chat belongs to farmer
        chat = Chat.query.filter_by(id=chat_id, farmer_id=farmer_id_verified).first()
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Get farmer name from session or database
        farmer = Farmer.query.filter_by(farmer_id=farmer_id_verified).first()
        farmer_name = farmer.name if farmer else "Farmer"
        
        data = request.get_json()
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Create message
        new_message = ChatMessage(
            chat_id=chat_id,
            sender_type='farmer',
            sender_id=farmer_id_verified,
            sender_name=farmer_name,
            message=message_text
        )
        
        # Update chat's last_message_at
        chat.last_message_at = datetime.utcnow()
        
        db.session.add(new_message)
        db.session.commit()
        
        return jsonify({
            'id': new_message.id,
            'message': new_message.message,
            'sender_type': new_message.sender_type,
            'created_at': new_message.created_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ===== EDIT PROFILE ROUTES =====

@auth_bp.route('/edit-profile', methods=['GET'])
@login_required
def edit_profile():
    """Serve edit profile page"""
    farmer_id = session.get('farmer_id_verified')
    farmer = Farmer.query.filter_by(id=farmer_id).first()
    
    if not farmer:
        return redirect(url_for('auth.login'))
    
    pre = farmer.to_dict()
    return render_template('edit_profile.html', pre=pre)


@auth_bp.route('/edit-profile', methods=['POST'])
@login_required
def edit_profile_post():
    """Process edit profile form"""
    farmer_id = session.get('farmer_id_verified')
    farmer = Farmer.query.filter_by(id=farmer_id).first()
    
    if not farmer:
        return redirect(url_for('auth.login'))
    
    try:
        # Update basic fields
        if request.form.get('name'):
            farmer.name = request.form.get('name').strip()
        
        if request.form.get('date_of_birth'):
            try:
                farmer.date_of_birth = datetime.strptime(request.form.get('date_of_birth'), "%Y-%m-%d")
            except:
                pass
        
        if request.form.get('gender'):
            farmer.gender = request.form.get('gender').strip()
        
        if request.form.get('caste_category'):
            farmer.caste_category = request.form.get('caste_category').strip()
        
        if request.form.get('permanent_address'):
            farmer.permanent_address = request.form.get('permanent_address').strip()
        
        if request.form.get('district'):
            farmer.district = request.form.get('district').strip()
        
        if request.form.get('taluka'):
            farmer.taluka = request.form.get('taluka').strip()
        
        if request.form.get('village'):
            farmer.village = request.form.get('village').strip()
        
        if request.form.get('state'):
            farmer.state = request.form.get('state').strip()
        
        if request.form.get('pincode'):
            farmer.pincode = request.form.get('pincode').strip()
        
        # Update farming fields
        if request.form.get('land_holder_type'):
            farmer.land_holder_type = request.form.get('land_holder_type').strip()
        
        if request.form.get('soil_type'):
            farmer.soil_type = request.form.get('soil_type').strip()
        
        if request.form.get('water_type'):
            farmer.water_type = request.form.get('water_type').strip()
        
        if request.form.get('current_crops'):
            farmer.current_crops = request.form.get('current_crops').strip()
        
        if request.form.get('land_area_gunthas'):
            try:
                farmer.land_area_gunthas = float(request.form.get('land_area_gunthas'))
            except:
                pass
        
        if request.form.get('total_land_area_hectares'):
            try:
                farmer.total_land_area_hectares = float(request.form.get('total_land_area_hectares'))
            except:
                pass
        
        if request.form.get('harvest_date'):
            try:
                farmer.harvest_date = datetime.strptime(request.form.get('harvest_date'), "%Y-%m-%d")
            except:
                pass
        
        # Update boolean fields
        is_oilseed = request.form.get('is_oilseed_farmer', '').lower() == 'yes'
        farmer.is_oilseed_farmer = is_oilseed
        
        is_pm_kisan = request.form.get('is_pm_kisan_beneficiary', '').lower() == 'yes'
        farmer.is_pm_kisan_beneficiary = is_pm_kisan
        
        is_handicapped = request.form.get('is_physically_handicapped', '').lower() == 'yes'
        farmer.is_physically_handicapped = is_handicapped
        
        # Update financial field
        if request.form.get('annual_income'):
            try:
                farmer.annual_income = float(request.form.get('annual_income'))
            except:
                pass
        
        # Handle profile picture upload
        if 'profile_pic' in request.files:
            pic_file = request.files['profile_pic']
            if pic_file and pic_file.filename:
                new_pic = save_profile_pic(pic_file, farmer.id)
                if new_pic:
                    farmer.profile_pic = new_pic
        
        farmer.updated_at = datetime.utcnow()
        db.session.commit()
        
        return redirect(url_for('auth.profile'))
    
    except Exception as e:
        db.session.rollback()
        return render_template('edit_profile.html', pre=farmer.to_dict(), error=str(e))

