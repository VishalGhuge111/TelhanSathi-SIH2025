from flask import Blueprint, render_template, request, jsonify, session, redirect
import os
from models import db, Notification, Farmer
from datetime import datetime
import uuid

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


# Development helper: quickly log in as the first farmer to test notifications
@notifications_bp.route('/dev-login-first')
def dev_login_first():
    """DEV ONLY: Set session as first farmer and redirect to notifications list.
    Enabled only when FLASK_ENV=development. Remove this route before production.
    """
    if os.getenv('FLASK_ENV') != 'development':
        return jsonify({'error': 'Not allowed in this environment'}), 403

    farmer = Farmer.query.first()
    if not farmer:
        return jsonify({'error': 'No farmer found to login as'}), 404

    session['farmer_id_verified'] = farmer.id
    return redirect('/notifications/list')



# ==================== PAGE ROUTES ====================

@notifications_bp.route('/list')
def notifications_list():
    """Display all notifications page"""
    if 'farmer_id_verified' not in session:
        return redirect('/login')
    return render_template('notifications_list.html')


@notifications_bp.route('/detail/<notification_id>')
def notification_detail(notification_id):
    """Display single notification detail page"""
    if 'farmer_id_verified' not in session:
        return redirect('/login')
    
    notification = Notification.query.get(notification_id)
    if not notification:
        return render_template('error.html', message='Notification not found'), 404
    
    # Mark as read if not already
    if not notification.is_read:
        notification.is_read = True
        db.session.commit()
    
    return render_template('notifications_detail.html', notification=notification)


# ==================== API ROUTES ====================

@notifications_bp.route('/api/list', methods=['GET'])
def api_notifications_list():
    """Get all notifications for the logged-in farmer (paginated)"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    farmer_id = session.get('farmer_id_verified')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    filter_type = request.args.get('type', None)  # Filter by notification type
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    query = Notification.query.filter_by(farmer_id=farmer_id)
    
    if unread_only:
        query = query.filter_by(is_read=False)
    
    if filter_type:
        query = query.filter_by(notification_type=filter_type)
    
    # Order by created_at descending (newest first)
    notifications = query.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'notifications': [n.to_dict() for n in notifications.items],
        'total': notifications.total,
        'pages': notifications.pages,
        'current_page': page
    })


@notifications_bp.route('/api/unread-count', methods=['GET'])
def api_unread_count():
    """Get count of unread notifications"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    farmer_id = session.get('farmer_id_verified')
    unread_count = Notification.query.filter_by(
        farmer_id=farmer_id, 
        is_read=False
    ).count()
    
    return jsonify({'unread_count': unread_count})


@notifications_bp.route('/api/detail/<notification_id>', methods=['GET'])
def api_notification_detail(notification_id):
    """Get single notification details"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    farmer_id = session.get('farmer_id_verified')
    notification = Notification.query.filter_by(
        id=notification_id,
        farmer_id=farmer_id
    ).first()
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    # Mark as read
    if not notification.is_read:
        notification.is_read = True
        db.session.commit()
    
    return jsonify(notification.to_dict())


@notifications_bp.route('/api/mark-as-read/<notification_id>', methods=['POST'])
def api_mark_as_read(notification_id):
    """Mark a notification as read"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    farmer_id = session.get('farmer_id_verified')
    notification = Notification.query.filter_by(
        id=notification_id,
        farmer_id=farmer_id
    ).first()
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Marked as read'})


@notifications_bp.route('/api/mark-all-as-read', methods=['POST'])
def api_mark_all_as_read():
    """Mark all notifications as read"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    farmer_id = session.get('farmer_id_verified')
    Notification.query.filter_by(
        farmer_id=farmer_id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'All notifications marked as read'})


@notifications_bp.route('/api/delete/<notification_id>', methods=['DELETE'])
def api_delete_notification(notification_id):
    """Delete a notification"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    farmer_id = session.get('farmer_id_verified')
    notification = Notification.query.filter_by(
        id=notification_id,
        farmer_id=farmer_id
    ).first()
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    db.session.delete(notification)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Notification deleted'})


@notifications_bp.route('/api/clear-all', methods=['DELETE'])
def api_clear_all():
    """Delete all notifications"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    farmer_id = session.get('farmer_id_verified')
    Notification.query.filter_by(farmer_id=farmer_id).delete()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'All notifications cleared'})


# ==================== ADMIN ROUTES ====================

@notifications_bp.route('/api/send', methods=['POST'])
def api_send_notification():
    """Admin: Send notification to a farmer"""
    # This would typically be an admin-only endpoint
    data = request.get_json()
    
    farmer_id = data.get('farmer_id')
    title = data.get('title')
    description = data.get('description')
    notification_type = data.get('type', 'general_alert')
    icon = data.get('icon', 'bell')
    color = data.get('color', 'info')
    related_id = data.get('related_id')
    related_type = data.get('related_type')
    action_link = data.get('action_link')
    is_important = data.get('is_important', False)
    
    if not all([farmer_id, title, description]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    notification = Notification(
        id=str(uuid.uuid4()),
        farmer_id=farmer_id,
        title=title,
        description=description,
        notification_type=notification_type,
        icon=icon,
        color=color,
        related_id=related_id,
        related_type=related_type,
        action_link=action_link,
        is_important=is_important
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Notification sent',
        'notification': notification.to_dict()
    }), 201
