from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from extensions import db
from models import Farmer
import sys, os
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
import secrets

# ensure imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', 'profile_pics')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Create upload folder if it doesn't exist
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

onboarding_bp = Blueprint('onboarding', __name__)


# ---------------------- GET ----------------------
@onboarding_bp.route('/onboarding', methods=['GET'])
def onboarding():
    """Render comprehensive onboarding form."""
    if 'farmer_id_verified' not in session:
        return redirect(url_for('auth.login'))

    farmer = Farmer.query.filter_by(id=session.get('farmer_id_verified')).first()

    pre = {
        'name': farmer.name if farmer and farmer.name else '',
        'district': farmer.district if farmer and farmer.district else '',
        'date_of_birth': farmer.date_of_birth.strftime("%Y-%m-%d") if farmer and farmer.date_of_birth else '',
        'gender': farmer.gender if farmer and farmer.gender else '',
        'caste_category': farmer.caste_category if farmer and farmer.caste_category else '',
        'permanent_address': farmer.permanent_address if farmer and farmer.permanent_address else '',
        'taluka': farmer.taluka if farmer and farmer.taluka else '',
        'village': farmer.village if farmer and farmer.village else '',
        'state': farmer.state if farmer and farmer.state else '',
        'pincode': farmer.pincode if farmer and farmer.pincode else '',
        'land_unit': farmer.land_unit if farmer and farmer.land_unit else 'acre',
        'is_oilseed_farmer': farmer.is_oilseed_farmer if farmer and farmer.is_oilseed_farmer else False,
        'land_holder_type': farmer.land_holder_type if farmer and farmer.land_holder_type else '',
        'land_area_gunthas': farmer.land_area_gunthas if farmer and farmer.land_area_gunthas else '',
        'soil_type': farmer.soil_type if farmer and farmer.soil_type else '',
        'water_type': farmer.water_type if farmer and farmer.water_type else '',
        'current_crops': farmer.current_crops if farmer and farmer.current_crops else '',
        'harvest_date': farmer.harvest_date.strftime("%Y-%m-%d") if farmer and farmer.harvest_date else '',
        'annual_income': farmer.annual_income if farmer and farmer.annual_income else '',
        'is_pm_kisan_beneficiary': farmer.is_pm_kisan_beneficiary if farmer and farmer.is_pm_kisan_beneficiary else False,
        'is_physically_handicapped': farmer.is_physically_handicapped if farmer and farmer.is_physically_handicapped else False,
    }

    return render_template('onboarding.html', pre=pre)



# ---------------------- POST ----------------------
@onboarding_bp.route('/onboarding', methods=['POST'])
def onboarding_post():
    """Process onboarding inputs and store into Farmer model."""
    if 'farmer_id_verified' not in session:
        return redirect(url_for('auth.login'))
    
    farmer = Farmer.query.filter_by(id=session.get('farmer_id_verified')).first()
    if not farmer:
        return redirect(url_for('auth.login'))
    
    # Collect all onboarding fields
    name = request.form.get('name', '').strip()
    district = request.form.get('district', '').strip()
    date_of_birth = request.form.get('date_of_birth', '').strip()
    gender = request.form.get('gender', '').strip()
    caste_category = request.form.get('caste_category', '').strip()
    is_physically_handicapped_input = request.form.get('is_physically_handicapped', '').strip().lower()
    is_physically_handicapped = is_physically_handicapped_input == 'yes'
    permanent_address = request.form.get('permanent_address', '').strip()
    taluka = request.form.get('taluka', '').strip()
    village = request.form.get('village', '').strip()
    state = request.form.get('state', '').strip()
    pincode = request.form.get('pincode', '').strip()
    land_unit = request.form.get('land_unit', 'acre').strip()
    is_oilseed_farmer_input = request.form.get('is_oilseed_farmer', '').strip().lower()
    is_oilseed_farmer = is_oilseed_farmer_input == 'yes'
    is_pm_kisan_beneficiary_input = request.form.get('is_pm_kisan_beneficiary', '').strip().lower()
    is_pm_kisan_beneficiary = is_pm_kisan_beneficiary_input == 'yes'
    land_holder_type = request.form.get('land_holder_type', '').strip()
    land_area_gunthas = request.form.get('land_area_gunthas', '').strip()
    total_land_area_hectares = request.form.get('total_land_area_hectares', '').strip()
    soil_type = request.form.get('soil_type', '').strip()
    water_type = request.form.get('water_type', '').strip()
    current_crops = request.form.get('current_crops', '').strip()
    harvest_date = request.form.get('harvest_date', '').strip()
    annual_income = request.form.get('annual_income', '').strip()
    
    # Handle profile picture upload
    profile_pic = None
    if 'profile_pic' in request.files:
        pic_file = request.files['profile_pic']
        if pic_file and pic_file.filename:
            profile_pic = save_profile_pic(pic_file, farmer.id)
    
    # Validate required fields
    if not name or not district:
        return render_template('onboarding.html', pre={
            'name': name, 'district': district, 'date_of_birth': date_of_birth,
            'gender': gender, 'caste_category': caste_category, 'is_physically_handicapped': is_physically_handicapped,
            'permanent_address': permanent_address, 'taluka': taluka, 'village': village, 'state': state, 'pincode': pincode,
            'land_unit': land_unit, 'is_oilseed_farmer': is_oilseed_farmer, 'land_holder_type': land_holder_type,
            'land_area_gunthas': land_area_gunthas, 'annual_income': annual_income, 'soil_type': soil_type,
            'water_type': water_type, 'current_crops': current_crops, 'harvest_date': harvest_date, 'is_pm_kisan_beneficiary': is_pm_kisan_beneficiary
        }, error='कृपया सभी आवश्यक फ़ील्ड भरें (नाम और जिला)')
    
    # Update farmer with all onboarding data
    farmer.name = name
    farmer.district = district
    if date_of_birth:
        try:
            farmer.date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d")
        except:
            pass
    if gender:
        farmer.gender = gender
    if caste_category:
        farmer.caste_category = caste_category
    farmer.is_physically_handicapped = is_physically_handicapped
    if permanent_address:
        farmer.permanent_address = permanent_address
    if taluka:
        farmer.taluka = taluka
    if village:
        farmer.village = village
    if state:
        farmer.state = state
    if pincode:
        farmer.pincode = pincode
    if land_unit:
        farmer.land_unit = land_unit
    
    farmer.is_oilseed_farmer = is_oilseed_farmer
    farmer.is_pm_kisan_beneficiary = is_pm_kisan_beneficiary
    
    if land_holder_type:
        farmer.land_holder_type = land_holder_type
    
    if soil_type:
        farmer.soil_type = soil_type
    
    if water_type:
        farmer.water_type = water_type
    
    if current_crops:
        farmer.current_crops = current_crops
    
    if harvest_date:
        try:
            farmer.harvest_date = datetime.strptime(harvest_date, "%Y-%m-%d")
        except:
            pass
    
    # Convert gunthas to number
    if land_area_gunthas:
        try:
            farmer.land_area_gunthas = float(land_area_gunthas)
        except:
            pass
    
    # Convert hectares to number
    if total_land_area_hectares:
        try:
            farmer.total_land_area_hectares = float(total_land_area_hectares)
        except:
            pass
    
    # Convert annual income to number
    if annual_income:
        try:
            farmer.annual_income = float(annual_income)
        except:
            pass
    
    # Ensure coins_earned is initialized to 0
    if farmer.coins_earned is None:
        farmer.coins_earned = 0
    
    # Save profile picture if uploaded
    if profile_pic:
        farmer.profile_pic = profile_pic
    
    # Mark onboarding as completed
    farmer.onboarding_completed = True
    
    db.session.commit()
    
    # Store in session
    session['user_context'] = {
        'name': name,
        'district': district,
        'soil_type': soil_type,
        'water_type': water_type
    }
    
    # Redirect to dashboard
    return redirect(url_for('dashboard'))


# ---------------------- API ----------------------
@onboarding_bp.route('/api/user_context', methods=['GET'])
def get_context():
    """Return user context & analysis JSON for frontend polling."""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'unauthenticated'}), 401

    return jsonify({
        'user_context': session.get('user_context'),
        'analysis': session.get('analysis')
    })


