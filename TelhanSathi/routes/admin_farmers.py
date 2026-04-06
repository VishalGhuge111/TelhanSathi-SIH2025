from flask import Blueprint, render_template, request, jsonify, session
from functools import wraps
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Farmer, CoinBalance, SubsidyApplication, FarmerRedemption
from extensions import db

admin_farmers_bp = Blueprint('admin_farmers', __name__, url_prefix='/admin')

# ===== AUTHENTICATION DECORATOR =====
def admin_login_required(f):
    """Decorator to check if admin is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ===== FARMER MANAGEMENT ROUTES =====

@admin_farmers_bp.route('/farmer-management', methods=['GET'])
@admin_login_required
def farmer_management():
    """Admin farmer management dashboard"""
    try:
        farmers = Farmer.query.all()
        
        # Calculate statistics
        redemptions = FarmerRedemption.query.all()
        total_coins_spent = sum([r.coins_spent for r in redemptions])
        
        stats = {
            'total_farmers': len(farmers),
            'verified_farmers': len([f for f in farmers if f.is_verified]),
            'active_farmers': len([f for f in farmers if f.onboarding_completed]),
            'total_coins_spent': total_coins_spent,
        }
        
        return render_template('admin_farmer_management.html', farmers=farmers, stats=stats)
    except Exception as e:
        return render_template('admin_farmer_management.html', 
                             farmers=[],
                             stats={
                                 'total_farmers': 0,
                                 'verified_farmers': 0,
                                 'active_farmers': 0,
                                 'total_coins_spent': 0,
                             },
                             error=f'Error loading farmers: {str(e)}')


# ===== API ENDPOINTS =====

@admin_farmers_bp.route('/api/farmers', methods=['GET'])
@admin_login_required
def api_get_farmers():
    """Get farmers with optional filtering"""
    try:
        # Get query parameters for filtering
        search = request.args.get('search', '').lower()
        district = request.args.get('district', '')
        verified = request.args.get('verified', '')
        
        query = Farmer.query
        
        # Apply filters
        if search:
            query = query.filter(
                db.or_(
                    Farmer.name.ilike(f'%{search}%'),
                    Farmer.phone_number.ilike(f'%{search}%'),
                    Farmer.farmer_id.ilike(f'%{search}%')
                )
            )
        
        if district:
            query = query.filter(Farmer.district == district)
        
        if verified and verified.lower() in ['true', 'false']:
            query = query.filter(Farmer.is_verified == (verified.lower() == 'true'))
        
        farmers = query.all()
        
        return jsonify({
            'success': True,
            'count': len(farmers),
            'farmers': [{
                'id': f.id,
                'farmer_id': f.farmer_id,
                'name': f.name,
                'phone_number': f.phone_number,
                'district': f.district,
                'is_verified': f.is_verified,
                'onboarding_completed': f.onboarding_completed,
                'coins_earned': f.coins_earned,
                'total_land_area': f.total_land_area_hectares,
                'current_crops': f.current_crops,
                'created_at': f.created_at.isoformat(),
            } for f in farmers]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_farmers_bp.route('/api/farmers/<farmer_id>', methods=['GET'])
@admin_login_required
def api_get_farmer_details(farmer_id):
    """Get detailed information about a specific farmer"""
    try:
        farmer = Farmer.query.filter_by(id=farmer_id).first()
        
        if not farmer:
            return jsonify({'success': False, 'error': 'Farmer not found'}), 404
        
        # Get subsidy applications
        subsidy_apps = SubsidyApplication.query.filter_by(farmer_id=farmer_id).all()
        
        # Get coin balance
        coin_balance = CoinBalance.query.filter_by(farmer_id=farmer_id).first()
        
        return jsonify({
            'success': True,
            'farmer': {
                'id': farmer.id,
                'farmer_id': farmer.farmer_id,
                'name': farmer.name,
                'phone_number': farmer.phone_number,
                'gender': farmer.gender,
                'date_of_birth': farmer.date_of_birth.isoformat() if farmer.date_of_birth else None,
                'district': farmer.district,
                'taluka': farmer.taluka,
                'village': farmer.village,
                'pincode': farmer.pincode,
                'total_land_area_hectares': farmer.total_land_area_hectares,
                'land_unit': farmer.land_unit,
                'current_crops': farmer.current_crops,
                'soil_type': farmer.soil_type,
                'water_type': farmer.water_type,
                'is_oilseed_farmer': farmer.is_oilseed_farmer,
                'is_pm_kisan_beneficiary': farmer.is_pm_kisan_beneficiary,
                'is_verified': farmer.is_verified,
                'onboarding_completed': farmer.onboarding_completed,
                'coins_earned': farmer.coins_earned,
                'created_at': farmer.created_at.isoformat(),
                'updated_at': farmer.updated_at.isoformat(),
                'subsidy_applications_count': len(subsidy_apps),
                'coin_balance': {
                    'total_coins': coin_balance.total_coins if coin_balance else 0,
                    'available_coins': coin_balance.available_coins if coin_balance else 0,
                    'redeemed_coins': coin_balance.redeemed_coins if coin_balance else 0,
                } if coin_balance else None
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_farmers_bp.route('/api/farmers/<farmer_id>/toggle-verify', methods=['POST'])
@admin_login_required
def api_toggle_farmer_verification(farmer_id):
    """Toggle farmer verification status"""
    try:
        farmer = Farmer.query.filter_by(id=farmer_id).first()
        
        if not farmer:
            return jsonify({'success': False, 'error': 'Farmer not found'}), 404
        
        # Toggle verification
        farmer.is_verified = not farmer.is_verified
        
        # Set verification timestamp if just verified
        if farmer.is_verified and not farmer.verification_timestamp:
            farmer.verification_timestamp = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f"Farmer {'verified' if farmer.is_verified else 'unverified'} successfully",
            'is_verified': farmer.is_verified
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_farmers_bp.route('/api/farmers/districts', methods=['GET'])
@admin_login_required
def api_get_districts():
    """Get list of all districts with farmers"""
    try:
        districts = db.session.query(Farmer.district).distinct().filter(Farmer.district.isnot(None)).all()
        district_list = [d[0] for d in districts if d[0]]
        district_list.sort()
        
        return jsonify({
            'success': True,
            'districts': district_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
