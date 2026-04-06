from flask import Blueprint, render_template, request, jsonify, session
from functools import wraps
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Scheme
from extensions import db

admin_schemes_bp = Blueprint('admin_schemes', __name__, url_prefix='/admin')

# ===== AUTHENTICATION DECORATOR =====
def admin_login_required(f):
    """Decorator to check if admin is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ===== SCHEME MANAGEMENT ROUTES =====

@admin_schemes_bp.route('/scheme-management', methods=['GET'])
@admin_login_required
def scheme_management():
    """Admin scheme management dashboard"""
    try:
        schemes = Scheme.query.all()
        stats = {
            'total_schemes': len(schemes),
            'active_schemes': len([s for s in schemes if s.is_active]),
            'recommended_schemes': len([s for s in schemes if s.is_recommended]),
        }
        return render_template('admin_scheme_management.html', schemes=schemes, stats=stats)
    except Exception as e:
        return render_template('admin_scheme_management.html', error=f'Error loading schemes: {str(e)}')


# ===== API ENDPOINTS =====

@admin_schemes_bp.route('/api/schemes', methods=['GET'])
@admin_login_required
def api_get_schemes():
    """Get all schemes"""
    try:
        schemes = Scheme.query.all()
        return jsonify([{
            'id': s.id,
            'scheme_code': s.scheme_code,
            'name': s.name,
            'description': s.description,
            'scheme_type': s.scheme_type,
            'focus_area': s.focus_area,
            'focus_color': s.focus_color,
            'benefit_amount': s.benefit_amount,
            'eligibility_criteria': s.eligibility_criteria,
            'is_active': s.is_active,
            'is_recommended': s.is_recommended,
            'external_link': s.external_link
        } for s in schemes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_schemes_bp.route('/api/schemes', methods=['POST'])
@admin_login_required
def api_create_scheme():
    """Create a new scheme"""
    try:
        data = request.get_json()
        
        # Validation
        required_fields = ['scheme_code', 'name', 'scheme_type', 'focus_area', 
                          'benefit_amount', 'eligibility_criteria', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if scheme code already exists
        existing = Scheme.query.filter_by(scheme_code=data['scheme_code']).first()
        if existing:
            return jsonify({'error': 'Scheme code already exists'}), 400
        
        # Create new scheme
        scheme = Scheme(
            scheme_code=data['scheme_code'],
            name=data['name'],
            description=data['description'],
            scheme_type=data['scheme_type'],
            focus_area=data['focus_area'],
            focus_color=data.get('focus_color', '#2196f3'),
            benefit_amount=data['benefit_amount'],
            eligibility_criteria=data['eligibility_criteria'],
            external_link=data.get('external_link'),
            is_recommended=data.get('is_recommended', False),
            is_active=data.get('is_active', True),
            apply_steps=json.dumps(data.get('apply_steps', [])),
            required_documents=json.dumps(data.get('required_documents', []))
        )
        
        db.session.add(scheme)
        db.session.commit()
        
        return jsonify({
            'message': 'Scheme created successfully',
            'scheme': {
                'id': scheme.id,
                'name': scheme.name,
                'scheme_code': scheme.scheme_code
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_schemes_bp.route('/api/schemes/<scheme_id>', methods=['GET'])
@admin_login_required
def api_get_scheme(scheme_id):
    """Get specific scheme details"""
    try:
        scheme = Scheme.query.get_or_404(scheme_id)
        return jsonify({
            'id': scheme.id,
            'scheme_code': scheme.scheme_code,
            'name': scheme.name,
            'description': scheme.description,
            'scheme_type': scheme.scheme_type,
            'focus_area': scheme.focus_area,
            'focus_color': scheme.focus_color,
            'benefit_amount': scheme.benefit_amount,
            'eligibility_criteria': scheme.eligibility_criteria,
            'external_link': scheme.external_link,
            'is_recommended': scheme.is_recommended,
            'is_active': scheme.is_active,
            'apply_steps': json.loads(scheme.apply_steps) if scheme.apply_steps else [],
            'required_documents': json.loads(scheme.required_documents) if scheme.required_documents else [],
            'created_at': scheme.created_at.isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_schemes_bp.route('/api/schemes/<scheme_id>', methods=['PUT'])
@admin_login_required
def api_update_scheme(scheme_id):
    """Update a scheme"""
    try:
        scheme = Scheme.query.get_or_404(scheme_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            scheme.name = data['name']
        if 'description' in data:
            scheme.description = data['description']
        if 'scheme_type' in data:
            scheme.scheme_type = data['scheme_type']
        if 'focus_area' in data:
            scheme.focus_area = data['focus_area']
        if 'focus_color' in data:
            scheme.focus_color = data['focus_color']
        if 'benefit_amount' in data:
            scheme.benefit_amount = data['benefit_amount']
        if 'eligibility_criteria' in data:
            scheme.eligibility_criteria = data['eligibility_criteria']
        if 'external_link' in data:
            scheme.external_link = data['external_link']
        if 'is_active' in data:
            scheme.is_active = data['is_active']
        if 'is_recommended' in data:
            scheme.is_recommended = data['is_recommended']
        
        db.session.commit()
        
        return jsonify({'message': 'Scheme updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_schemes_bp.route('/api/schemes/<scheme_id>', methods=['DELETE'])
@admin_login_required
def api_delete_scheme(scheme_id):
    """Delete a scheme"""
    try:
        scheme = Scheme.query.get_or_404(scheme_id)
        db.session.delete(scheme)
        db.session.commit()
        
        return jsonify({'message': 'Scheme deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_schemes_bp.route('/api/schemes/<scheme_id>/toggle', methods=['POST'])
@admin_login_required
def api_toggle_scheme(scheme_id):
    """Toggle scheme active/inactive status"""
    try:
        scheme = Scheme.query.get_or_404(scheme_id)
        scheme.is_active = not scheme.is_active
        db.session.commit()
        
        return jsonify({
            'message': 'Scheme status updated',
            'is_active': scheme.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_schemes_bp.route('/api/schemes/<scheme_id>/recommend', methods=['POST'])
@admin_login_required
def api_toggle_recommend_scheme(scheme_id):
    """Toggle scheme recommended status"""
    try:
        scheme = Scheme.query.get_or_404(scheme_id)
        scheme.is_recommended = not scheme.is_recommended
        db.session.commit()
        
        return jsonify({
            'message': 'Scheme recommendation updated',
            'is_recommended': scheme.is_recommended
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
