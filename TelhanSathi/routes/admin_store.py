from flask import Blueprint, render_template, request, jsonify, session
from functools import wraps
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import RedemptionOffer, FarmerRedemption
from extensions import db

admin_store_bp = Blueprint('admin_store', __name__, url_prefix='/admin')

# ===== AUTHENTICATION DECORATOR =====
def admin_login_required(f):
    """Decorator to check if admin is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ===== STORE MANAGEMENT ROUTES =====

@admin_store_bp.route('/store-management', methods=['GET'])
@admin_login_required
def store_management():
    """Admin store management dashboard"""
    try:
        offers = RedemptionOffer.query.all()
        redemptions = FarmerRedemption.query.all()
        
        total_coins_spent = sum([r.coins_spent for r in redemptions])
        
        stats = {
            'total_offers': len(offers),
            'active_offers': len([o for o in offers if o.is_active]),
            'total_coins_spent': total_coins_spent,
        }
        return render_template('admin_store_management.html', offers=offers, stats=stats)
    except Exception as e:
        return render_template('admin_store_management.html', error=f'Error loading store: {str(e)}')


# ===== API ENDPOINTS =====

@admin_store_bp.route('/api/offers', methods=['GET'])
@admin_login_required
def api_get_offers():
    """Get all redemption offers"""
    try:
        offers = RedemptionOffer.query.all()
        return jsonify([{
            'id': o.id,
            'title': o.title,
            'description': o.description,
            'category': o.category,
            'coin_cost': o.coin_cost,
            'actual_value': o.actual_value,
            'is_active': o.is_active,
            'stock_limit': o.stock_limit,
            'stock_redeemed': o.stock_redeemed,
            'icon': o.icon,
            'color': o.color
        } for o in offers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_store_bp.route('/api/offers', methods=['POST'])
@admin_login_required
def api_create_offer():
    """Create a new redemption offer"""
    try:
        data = request.get_json()
        
        # Validation
        required_fields = ['title', 'description', 'category', 'coin_cost', 'actual_value']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create new offer
        offer = RedemptionOffer(
            title=data['title'],
            description=data['description'],
            category=data['category'],
            coin_cost=int(data['coin_cost']),
            actual_value=data['actual_value'],
            offer_type=data.get('offer_type', 'offer'),
            validity_days=data.get('validity_days', 90),
            stock_limit=data.get('stock_limit'),
            is_active=data.get('is_active', True),
            icon=data.get('icon', '🎁'),
            color=data.get('color', '#388e3c')
        )
        
        db.session.add(offer)
        db.session.commit()
        
        return jsonify({
            'message': 'Offer created successfully',
            'offer': {
                'id': offer.id,
                'title': offer.title,
                'coin_cost': offer.coin_cost
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_store_bp.route('/api/offers/<offer_id>', methods=['GET'])
@admin_login_required
def api_get_offer(offer_id):
    """Get specific offer details"""
    try:
        offer = RedemptionOffer.query.get_or_404(offer_id)
        return jsonify({
            'id': offer.id,
            'title': offer.title,
            'description': offer.description,
            'category': offer.category,
            'coin_cost': offer.coin_cost,
            'actual_value': offer.actual_value,
            'offer_type': offer.offer_type,
            'validity_days': offer.validity_days,
            'is_active': offer.is_active,
            'stock_limit': offer.stock_limit,
            'stock_redeemed': offer.stock_redeemed,
            'icon': offer.icon,
            'color': offer.color,
            'created_at': offer.created_at.isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_store_bp.route('/api/offers/<offer_id>', methods=['PUT'])
@admin_login_required
def api_update_offer(offer_id):
    """Update an offer"""
    try:
        offer = RedemptionOffer.query.get_or_404(offer_id)
        data = request.get_json()
        
        # Update fields
        if 'title' in data:
            offer.title = data['title']
        if 'description' in data:
            offer.description = data['description']
        if 'category' in data:
            offer.category = data['category']
        if 'coin_cost' in data:
            offer.coin_cost = int(data['coin_cost'])
        if 'actual_value' in data:
            offer.actual_value = data['actual_value']
        if 'is_active' in data:
            offer.is_active = data['is_active']
        if 'stock_limit' in data:
            offer.stock_limit = data.get('stock_limit')
        if 'icon' in data:
            offer.icon = data['icon']
        if 'color' in data:
            offer.color = data['color']
        
        db.session.commit()
        
        return jsonify({'message': 'Offer updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_store_bp.route('/api/offers/<offer_id>', methods=['DELETE'])
@admin_login_required
def api_delete_offer(offer_id):
    """Delete an offer"""
    try:
        offer = RedemptionOffer.query.get_or_404(offer_id)
        db.session.delete(offer)
        db.session.commit()
        
        return jsonify({'message': 'Offer deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_store_bp.route('/api/offers/<offer_id>/toggle', methods=['POST'])
@admin_login_required
def api_toggle_offer(offer_id):
    """Toggle offer active/inactive status"""
    try:
        offer = RedemptionOffer.query.get_or_404(offer_id)
        offer.is_active = not offer.is_active
        db.session.commit()
        
        return jsonify({
            'message': 'Offer status updated',
            'is_active': offer.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
