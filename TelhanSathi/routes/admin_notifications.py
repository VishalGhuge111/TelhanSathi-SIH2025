from flask import Blueprint, render_template, request, jsonify, session
from functools import wraps
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Farmer, Notification
from extensions import db

admin_notifications_bp = Blueprint('admin_notifications', __name__, url_prefix='/admin')

# ===== AUTHENTICATION DECORATOR =====
def admin_login_required(f):
    """Decorator to check if admin is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ===== NOTIFICATIONS MANAGEMENT ROUTES =====

@admin_notifications_bp.route('/notifications-management', methods=['GET'])
@admin_login_required
def notifications_management():
    """Admin notifications management dashboard"""
    try:
        notifications = Notification.query.all()
        farmers = Farmer.query.all()
        
        # Create a dictionary for farmer lookup in template
        farmer_dict = {farmer.id: farmer.name for farmer in farmers}
        
        stats = {
            'total_notifications': len(notifications),
            'unread_notifications': len([n for n in notifications if not n.is_read]),
            'important_notifications': len([n for n in notifications if n.is_important]),
            'total_farmers': len(farmers),
        }
        
        return render_template('admin_notifications_management.html', 
                             notifications=notifications, 
                             farmers=farmers,
                             farmer_dict=farmer_dict,
                             stats=stats)
    except Exception as e:
        return render_template('admin_notifications_management.html', 
                             farmers=[],
                             farmer_dict={},
                             stats={'total_notifications': 0, 'unread_notifications': 0, 'important_notifications': 0, 'total_farmers': 0},
                             error=f'Error loading notifications: {str(e)}')


# ===== API ENDPOINTS =====

@admin_notifications_bp.route('/api/notifications', methods=['GET'])
@admin_login_required
def api_get_notifications():
    """Get all notifications"""
    try:
        notifications = Notification.query.all()
        return jsonify([{
            'id': n.id,
            'farmer_id': n.farmer_id,
            'farmer_name': Farmer.query.get(n.farmer_id).name if Farmer.query.get(n.farmer_id) else 'Unknown',
            'title': n.title,
            'description': n.description,
            'notification_type': n.notification_type,
            'is_read': n.is_read,
            'is_important': n.is_important,
            'icon': n.icon,
            'color': n.color,
            'created_at': n.created_at.isoformat()
        } for n in notifications])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_notifications_bp.route('/api/notifications', methods=['POST'])
@admin_login_required
def api_create_notification():
    """Create a new notification for all farmers"""
    try:
        data = request.get_json()
        
        # Validation
        required_fields = ['title', 'description', 'notification_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get all farmers
        farmers = Farmer.query.all()
        if not farmers:
            return jsonify({'error': 'No farmers found in system'}), 404
        
        # Create notifications for all farmers
        notifications_created = 0
        for farmer in farmers:
            notification = Notification(
                farmer_id=farmer.id,
                title=data['title'],
                description=data['description'],
                notification_type=data['notification_type'],
                icon=data.get('icon', '📢'),
                color=data.get('color', '#2196f3'),
                is_important=data.get('is_important', False),
                is_read=False
            )
            db.session.add(notification)
            notifications_created += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'Notification sent to {notifications_created} farmers successfully',
            'notifications_count': notifications_created
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_notifications_bp.route('/api/notifications/<notification_id>', methods=['GET'])
@admin_login_required
def api_get_notification(notification_id):
    """Get specific notification details"""
    try:
        notification = Notification.query.get_or_404(notification_id)
        farmer = Farmer.query.get(notification.farmer_id)
        
        return jsonify({
            'id': notification.id,
            'farmer_id': notification.farmer_id,
            'farmer_name': farmer.name if farmer else 'Unknown',
            'title': notification.title,
            'description': notification.description,
            'notification_type': notification.notification_type,
            'icon': notification.icon,
            'color': notification.color,
            'is_important': notification.is_important,
            'is_read': notification.is_read,
            'action_link': notification.action_link,
            'created_at': notification.created_at.isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_notifications_bp.route('/api/notifications/<notification_id>', methods=['PUT'])
@admin_login_required
def api_update_notification(notification_id):
    """Update a notification"""
    try:
        notification = Notification.query.get_or_404(notification_id)
        data = request.get_json()
        
        # Update fields
        if 'title' in data:
            notification.title = data['title']
        if 'description' in data:
            notification.description = data['description']
        if 'notification_type' in data:
            notification.notification_type = data['notification_type']
        if 'icon' in data:
            notification.icon = data['icon']
        if 'color' in data:
            notification.color = data['color']
        if 'is_important' in data:
            notification.is_important = data['is_important']
        if 'is_read' in data:
            notification.is_read = data['is_read']
        if 'action_link' in data:
            notification.action_link = data['action_link']
        
        db.session.commit()
        
        return jsonify({'message': 'Notification updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_notifications_bp.route('/api/notifications/<notification_id>', methods=['DELETE'])
@admin_login_required
def api_delete_notification(notification_id):
    """Delete a notification"""
    try:
        notification = Notification.query.get_or_404(notification_id)
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({'message': 'Notification deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_notifications_bp.route('/api/notifications/<notification_id>/toggle-read', methods=['POST'])
@admin_login_required
def api_toggle_read_notification(notification_id):
    """Toggle notification read status"""
    try:
        notification = Notification.query.get_or_404(notification_id)
        notification.is_read = not notification.is_read
        db.session.commit()
        
        return jsonify({
            'message': 'Notification read status updated',
            'is_read': notification.is_read
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_notifications_bp.route('/api/notifications/<notification_id>/toggle-important', methods=['POST'])
@admin_login_required
def api_toggle_important_notification(notification_id):
    """Toggle notification important status"""
    try:
        notification = Notification.query.get_or_404(notification_id)
        notification.is_important = not notification.is_important
        db.session.commit()
        
        return jsonify({
            'message': 'Notification importance updated',
            'is_important': notification.is_important
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_notifications_bp.route('/api/farmers-list', methods=['GET'])
@admin_login_required
def api_get_farmers_list():
    """Get list of all farmers for dropdown"""
    try:
        farmers = Farmer.query.all()
        return jsonify({
            'success': True,
            'farmers': [{
                'id': f.id,
                'name': f.name,
                'farmer_id': f.farmer_id,
                'phone_number': f.phone_number
            } for f in farmers]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
