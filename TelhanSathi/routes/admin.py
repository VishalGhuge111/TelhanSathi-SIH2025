from flask import Blueprint, render_template, jsonify, request
from extensions import db
from models import Scheme
import json

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/subsidies")
def admin_subsidies():
    """Admin panel to manage schemes and subsidies"""
    return render_template("admin_subsidies.html")


# API Routes for Admin

@admin_bp.route("/api/schemes/list")
def api_schemes_list():
    """Get all schemes (admin view)"""
    schemes = Scheme.query.all()
    return jsonify([scheme.to_dict() for scheme in schemes])


@admin_bp.route("/api/schemes/detail/<scheme_id>")
def api_schemes_detail(scheme_id):
    """Get specific scheme details"""
    scheme = Scheme.query.get_or_404(scheme_id)
    return jsonify(scheme.to_dict())


@admin_bp.route("/api/schemes/add", methods=["POST"])
def api_schemes_add():
    """Add a new scheme/subsidy"""
    data = request.get_json()

    # Validate required fields
    required_fields = ['scheme_code', 'name', 'scheme_type', 'focus_area', 'benefit_amount', 
                       'eligibility_criteria', 'description']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Check if scheme code already exists
    existing = Scheme.query.filter_by(scheme_code=data['scheme_code']).first()
    if existing:
        return jsonify({"error": "Scheme code already exists"}), 400

    # Create new scheme
    scheme = Scheme(
        scheme_code=data['scheme_code'],
        name=data['name'],
        scheme_type=data['scheme_type'],
        focus_area=data['focus_area'],
        focus_color=data.get('focus_color', '#2196f3'),
        benefit_amount=data['benefit_amount'],
        eligibility_criteria=data['eligibility_criteria'],
        description=data['description'],
        external_link=data.get('external_link'),
        is_recommended=data.get('is_recommended', False),
        is_active=data.get('is_active', True),
        apply_steps=json.dumps(data.get('apply_steps', [])),
        required_documents=json.dumps(data.get('required_documents', []))
    )

    db.session.add(scheme)
    db.session.commit()

    return jsonify({
        "success": True,
        "scheme_id": scheme.id,
        "message": "Scheme added successfully"
    }), 201


@admin_bp.route("/api/schemes/update/<scheme_id>", methods=["PUT"])
def api_schemes_update(scheme_id):
    """Update a scheme/subsidy"""
    scheme = Scheme.query.get_or_404(scheme_id)
    data = request.get_json()

    # Update fields if provided
    if 'name' in data:
        scheme.name = data['name']
    if 'benefit_amount' in data:
        scheme.benefit_amount = data['benefit_amount']
    if 'eligibility_criteria' in data:
        scheme.eligibility_criteria = data['eligibility_criteria']
    if 'is_recommended' in data:
        scheme.is_recommended = data['is_recommended']
    if 'is_active' in data:
        scheme.is_active = data['is_active']
    if 'apply_steps' in data:
        scheme.apply_steps = json.dumps(data['apply_steps'])
    if 'required_documents' in data:
        scheme.required_documents = json.dumps(data['required_documents'])

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Scheme updated successfully"
    })


@admin_bp.route("/api/schemes/delete/<scheme_id>", methods=["DELETE"])
def api_schemes_delete(scheme_id):
    """Delete a scheme/subsidy"""
    scheme = Scheme.query.get_or_404(scheme_id)
    
    db.session.delete(scheme)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Scheme deleted successfully"
    })
