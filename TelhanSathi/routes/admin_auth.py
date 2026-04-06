from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import sys
import os

# Avoid circular imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Admin
from extensions import db

admin_auth_bp = Blueprint('admin_auth', __name__)

# ===== ADMIN AUTHENTICATION DECORATOR =====
def admin_login_required(f):
    """Decorator to check if admin is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_auth.admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ===== ADMIN SIGNUP ROUTES =====

@admin_auth_bp.route('/admin/signup', methods=['GET'])
def admin_signup():
    """Serve admin signup page"""
    return render_template('admin_signup.html')


@admin_auth_bp.route('/admin/signup', methods=['POST'])
def admin_signup_submit():
    """Handle admin signup"""
    try:
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        
        # Validation
        if not all([email, password, full_name]):
            return render_template('admin_signup.html', error='Please fill all required fields')
        
        if len(password) < 8:
            return render_template('admin_signup.html', error='Password must be at least 8 characters long')
        
        if password != confirm_password:
            return render_template('admin_signup.html', error='Passwords do not match')
        
        if not '@' in email:
            return render_template('admin_signup.html', error='Please enter a valid email address')
        
        # Check if admin already exists
        existing_admin = Admin.query.filter_by(email=email).first()
        if existing_admin:
            return render_template('admin_signup.html', error='Email already registered as admin')
        
        # Create new admin
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        new_admin = Admin(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            phone_number=phone_number,
            is_active=True,
            is_verified=True,  # In production, implement email verification
            role='admin'
        )
        
        db.session.add(new_admin)
        db.session.commit()
        
        # Log the admin in
        session['admin_id'] = new_admin.id
        session['admin_email'] = new_admin.email
        session['admin_name'] = new_admin.full_name
        session['admin_role'] = new_admin.role
        
        return redirect(url_for('admin_auth.admin_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        return render_template('admin_signup.html', error=f'An error occurred: {str(e)}')


# ===== ADMIN LOGIN ROUTES =====

@admin_auth_bp.route('/admin/login', methods=['GET'])
def admin_login():
    """Serve admin login page"""
    return render_template('admin_login.html')


@admin_auth_bp.route('/admin/login', methods=['POST'])
def admin_login_submit():
    """Handle admin login"""
    try:
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            return render_template('admin_login.html', error='Please enter email and password')
        
        # Find admin by email
        admin = Admin.query.filter_by(email=email).first()
        
        if not admin:
            return render_template('admin_login.html', error='Invalid email or password')
        
        # Check if admin is active
        if not admin.is_active:
            return render_template('admin_login.html', error='Your admin account has been deactivated')
        
        # Verify password
        if not check_password_hash(admin.password_hash, password):
            return render_template('admin_login.html', error='Invalid email or password')
        
        # Update last login
        admin.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create session
        session['admin_id'] = admin.id
        session['admin_email'] = admin.email
        session['admin_name'] = admin.full_name
        session['admin_role'] = admin.role
        
        return redirect(url_for('admin_auth.admin_dashboard'))
        
    except Exception as e:
        return render_template('admin_login.html', error=f'An error occurred: {str(e)}')


# ===== ADMIN DASHBOARD ROUTES =====

@admin_auth_bp.route('/admin/dashboard', methods=['GET'])
@admin_login_required
def admin_dashboard():
    """Admin dashboard - main page"""
    try:
        from models import Farmer, Scheme, SubsidyApplication
        
        # Get statistics
        total_farmers = Farmer.query.count()
        verified_farmers = Farmer.query.filter_by(is_verified=True).count()
        total_schemes = Scheme.query.count()
        active_schemes = Scheme.query.filter_by(is_active=True).count()
        total_applications = SubsidyApplication.query.count()
        pending_applications = SubsidyApplication.query.filter_by(status='Applied').count()
        
        stats = {
            'total_farmers': total_farmers,
            'verified_farmers': verified_farmers,
            'onboarding_completed': Farmer.query.filter_by(onboarding_completed=True).count(),
            'total_schemes': total_schemes,
            'active_schemes': active_schemes,
            'total_applications': total_applications,
            'pending_applications': pending_applications,
            'approved_applications': SubsidyApplication.query.filter_by(status='Approved').count(),
        }
        
        return render_template('admin_dashboard.html', stats=stats, admin_name=session.get('admin_name'))
        
    except Exception as e:
        return render_template('admin_dashboard.html', error=f'Error loading dashboard: {str(e)}')


# ===== ADMIN LOGOUT =====

@admin_auth_bp.route('/admin/logout', methods=['GET'])
def admin_logout():
    """Logout admin"""
    session.clear()
    return redirect(url_for('admin_auth.admin_login'))


# ===== ADMIN API ROUTES =====

@admin_auth_bp.route('/api/admin/profile', methods=['GET'])
@admin_login_required
def api_admin_profile():
    """Get current admin profile"""
    try:
        admin = Admin.query.get(session.get('admin_id'))
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        return jsonify(admin.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_auth_bp.route('/api/admin/profile', methods=['PUT'])
@admin_login_required
def api_admin_profile_update():
    """Update admin profile"""
    try:
        admin = Admin.query.get(session.get('admin_id'))
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'full_name' in data:
            admin.full_name = data['full_name']
        if 'phone_number' in data:
            admin.phone_number = data['phone_number']
        
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully', 'admin': admin.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_auth_bp.route('/api/admin/change-password', methods=['POST'])
@admin_login_required
def api_admin_change_password():
    """Change admin password"""
    try:
        admin = Admin.query.get(session.get('admin_id'))
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Verify current password
        if not check_password_hash(admin.password_hash, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Validate new password
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters long'}), 400
        
        if new_password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        # Update password
        admin.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
