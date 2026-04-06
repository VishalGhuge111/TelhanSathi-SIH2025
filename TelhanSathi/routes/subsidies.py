from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from extensions import db
from models import Scheme, SubsidyApplication, Farmer, FarmerRecommendation
import os
import json
from datetime import datetime, timedelta

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Cache for smart recommendations (farmer_id -> recommendations)
RECOMMENDATIONS_CACHE = {}
CACHE_EXPIRY = timedelta(hours=24)

subsidies_bp = Blueprint("subsidies", __name__, url_prefix="/subsidies")


@subsidies_bp.route("/list")
def subsidies_list():
    """Display list of all subsidies and schemes"""
    if "farmer_id_verified" not in session:
        return redirect(url_for("auth.login"))
    
    return render_template("subsidies_list.html")


@subsidies_bp.route("/api/list")
def api_subsidies_list():
    """API endpoint to get all active schemes/subsidies as JSON
    Query params:
    - type: 'subsidy' or 'scheme' to filter by type
    - filter_type: legacy parameter for backward compatibility
    """
    if "farmer_id_verified" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    # Get filter from query parameters
    filter_type = request.args.get('type') or request.args.get('filter_type')
    
    query = Scheme.query.filter_by(is_active=True)
    
    # Filter by scheme_type if specified
    if filter_type in ['subsidy', 'scheme']:
        query = query.filter_by(scheme_type=filter_type)
    
    schemes = query.all()
    return jsonify([scheme.to_dict() for scheme in schemes])


@subsidies_bp.route("/api/recommended")
def api_subsidies_recommended():
    """API endpoint to get recommended schemes for the farmer
    Query params:
    - type: 'subsidy' or 'scheme' to filter by type
    """
    if "farmer_id_verified" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    filter_type = request.args.get('type')
    
    query = Scheme.query.filter_by(is_active=True, is_recommended=True)
    
    # Filter by scheme_type if specified
    if filter_type in ['subsidy', 'scheme']:
        query = query.filter_by(scheme_type=filter_type)
    
    schemes = query.all()
    return jsonify([scheme.to_dict() for scheme in schemes])


@subsidies_bp.route("/detail/<scheme_id>")
def subsidies_detail(scheme_id):
    """Display details of a specific subsidy"""
    if "farmer_id_verified" not in session:
        return redirect(url_for("auth.login"))
    
    scheme = Scheme.query.get_or_404(scheme_id)
    
    return render_template("subsidies_detail.html", scheme_id=scheme_id)


@subsidies_bp.route("/api/detail/<scheme_id>")
def api_subsidies_detail(scheme_id):
    """API endpoint to get subsidy details as JSON"""
    if "farmer_id_verified" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    scheme = Scheme.query.get_or_404(scheme_id)
    
    return jsonify(scheme.to_dict())


@subsidies_bp.route("/api/apply/<scheme_id>", methods=["POST"])
def api_apply_scheme(scheme_id):
    """API endpoint to apply for a scheme"""
    if "farmer_id_verified" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    farmer_id = session["farmer_id_verified"]
    scheme = Scheme.query.get_or_404(scheme_id)
    
    # Create subsidy application
    application = SubsidyApplication(
        farmer_id=farmer_id,
        scheme_id=scheme_id,
        status="Applied",
        application_data=request.get_json().get("data", "{}")
    )
    
    db.session.add(application)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "application_id": application.id,
        "message": f"Successfully applied for {scheme.name}"
    }), 201


@subsidies_bp.route("/api/my-applications")
def api_my_applications():
    """API endpoint to get farmer's subsidy applications"""
    if "farmer_id_verified" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    farmer_id = session["farmer_id_verified"]
    applications = SubsidyApplication.query.filter_by(farmer_id=farmer_id).all()
    
    result = []
    for app in applications:
        result.append({
            'id': app.id,
            'scheme_id': app.scheme_id,
            'scheme_name': app.scheme.name if app.scheme else 'Unknown',
            'status': app.status,
            'application_date': app.application_date.isoformat() if app.application_date else None,
            'approved_amount': app.approved_amount,
            'approval_date': app.approval_date.isoformat() if app.approval_date else None
        })
    
    return jsonify(result)


@subsidies_bp.route("/api/ai-recommendations")
def api_ai_recommendations():
    """
    Get stored AI recommendations for the farmer from database
    Returns cached recommendations if available and fresh
    """
    if "farmer_id_verified" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        farmer_id = session["farmer_id_verified"]
        
        # Check if fresh recommendations exist (less than 24 hours old)
        fresh_recs = FarmerRecommendation.query.filter(
            FarmerRecommendation.farmer_id == farmer_id,
            FarmerRecommendation.expires_at > datetime.now()
        ).order_by(FarmerRecommendation.created_at.desc()).all()
        
        if fresh_recs:
            return jsonify({
                "success": True,
                "recommended_schemes": [rec.to_dict() for rec in fresh_recs],
                "from_cache": True,
                "ai_powered": fresh_recs[0].ai_method == 'gemini' if fresh_recs else False
            })
        
        return jsonify({
            "success": False,
            "message": "No recommendations available. Click 'Analyze' to generate new recommendations."
        }), 404
    
    except Exception as e:
        print(f"Error fetching AI recommendations: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@subsidies_bp.route("/api/smart-recommendations", methods=["GET", "POST"])
def api_smart_recommendations():
    """
    AI-powered smart recommendations using Gemini API with intelligent fallback
    Based on farmer profile data (land, crops, caste, disability, location, etc.)
    Returns personalized scheme recommendations and saves to database
    """
    if "farmer_id_verified" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        farmer_id = session["farmer_id_verified"]
        farmer = Farmer.query.filter_by(id=farmer_id).first()
        
        if not farmer:
            return jsonify({"error": "Farmer not found"}), 404
        
        # Clear old recommendations (older than 24 hours)
        FarmerRecommendation.query.filter(
            FarmerRecommendation.farmer_id == farmer_id,
            FarmerRecommendation.expires_at <= datetime.now()
        ).delete()
        db.session.commit()
        
        # Try Gemini API first
        recommended_schemes = None
        ai_method = None
        
        if GEMINI_AVAILABLE:
            gemini_result = _get_gemini_recommendations(farmer)
            if gemini_result and gemini_result.get('success'):
                recommended_schemes = gemini_result['recommended_schemes']
                ai_method = 'gemini'
        
        # Fallback to rule-based recommendations
        if not recommended_schemes:
            recommended_schemes = _get_rule_based_recommendations(farmer)
            ai_method = 'rule_based'
        
        if recommended_schemes:
            # Save recommendations to database
            expiry_time = datetime.now() + timedelta(hours=24)
            
            for rec in recommended_schemes:
                # Find the scheme ID
                scheme_id = None
                if 'id' in rec:
                    scheme_id = rec['id']
                elif 'scheme_id' in rec:
                    scheme_id = rec['scheme_id']
                
                if scheme_id:
                    # Delete old recommendation for this scheme
                    FarmerRecommendation.query.filter_by(
                        farmer_id=farmer_id,
                        scheme_id=scheme_id
                    ).delete()
                    
                    # Create new recommendation
                    farm_rec = FarmerRecommendation(
                        farmer_id=farmer_id,
                        scheme_id=scheme_id,
                        priority=rec.get('priority', 'medium'),
                        match_percentage=rec.get('match_percentage', 75),
                        reason=rec.get('reason', ''),
                        ai_method=ai_method,
                        expires_at=expiry_time
                    )
                    db.session.add(farm_rec)
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "recommended_schemes": recommended_schemes,
                "ai_powered": ai_method == 'gemini',
                "method": ai_method,
                "saved_to_db": True
            }), 201
        
        return jsonify({"success": False, "message": "Could not generate recommendations"}), 500
    
    except Exception as e:
        print(f"Error in smart recommendations: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _get_gemini_recommendations(farmer):
    """Get recommendations using Gemini API with quota handling"""
    try:
        # Get all available schemes
        all_schemes = Scheme.query.filter_by(is_active=True).all()
        schemes_list = [
            {
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'benefit_amount': s.benefit_amount,
                'eligibility': s.eligibility_criteria,
                'focus_area': s.focus_area,
                'scheme_type': s.scheme_type
            }
            for s in all_schemes
        ]
        
        # Build farmer profile summary
        farmer_profile = {
            'name': farmer.name,
            'state': farmer.state,
            'district': farmer.district,
            'taluka': farmer.taluka,
            'village': farmer.village,
            'land_area_hectares': farmer.total_land_area_hectares,
            'soil_type': farmer.soil_type,
            'current_crops': farmer.current_crops,
            'caste_category': farmer.caste_category,
            'is_oilseed_farmer': farmer.is_oilseed_farmer,
            'is_pm_kisan_beneficiary': farmer.is_pm_kisan_beneficiary,
            'land_holder_type': farmer.land_holder_type
        }
        
        # Initialize Gemini API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return None
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Create intelligent prompt
        prompt = f"""
You are an agricultural subsidy and scheme recommendation expert for Indian farmers.

FARMER PROFILE:
{json.dumps(farmer_profile, indent=2)}

AVAILABLE SCHEMES & SUBSIDIES:
{json.dumps(schemes_list, indent=2)}

Based on the farmer's profile, recommend TOP 5 most relevant schemes.

Consider:
1. Land area and type
2. Current crops (especially oilseeds)
3. Caste category eligibility
4. Disability benefits
5. Geographic location
6. Income level
7. Existing beneficiary status

Return ONLY valid JSON:
{{
    "recommended_schemes": [
        {{"scheme_id": "id", "priority": "high", "match_percentage": 90, "reason": "Why suitable"}}
    ]
}}
"""
        
        # Call Gemini API
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            recommendations = json.loads(json_str)
        else:
            return None
        
        # Enhance recommendations with actual scheme data
        all_schemes_dict = {s.id: s for s in all_schemes}
        if "recommended_schemes" in recommendations:
            enhanced_schemes = []
            for rec in recommendations["recommended_schemes"]:
                scheme = all_schemes_dict.get(rec.get("scheme_id"))
                if scheme:
                    enhanced_schemes.append({
                        'id': scheme.id,
                        'name': scheme.name,
                        'description': scheme.description,
                        'benefit_amount': scheme.benefit_amount,
                        'eligibility_criteria': scheme.eligibility_criteria,
                        'focus_area': scheme.focus_area,
                        'focus_color': scheme.focus_color,
                        'external_link': scheme.external_link,
                        'reason': rec.get('reason', ''),
                        'priority': rec.get('priority', 'medium'),
                        'match_percentage': rec.get('match_percentage', 75),
                        'ai_method': 'gemini'
                    })
            
            return {
                "success": True,
                "recommended_schemes": enhanced_schemes,
                "ai_powered": True
            }
        
        return None
    
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        return None


def _get_rule_based_recommendations(farmer):
    """Rule-based recommendation fallback (no API calls)"""
    try:
        recommendations = []
        all_schemes = Scheme.query.filter_by(is_active=True).all()
        
        # Score each scheme based on farmer profile
        scheme_scores = []
        
        for scheme in all_schemes:
            score = 0
            reason = ""
            
            # PM-KISAN - all farmers eligible
            if "PM-KISAN" in scheme.name:
                score = 90
                reason = "Universal income support scheme - you are eligible"
            
            # Oilseed programs - if oilseed farmer or in oilseed districts
            elif "oilseed" in scheme.name.lower() or "NMEO" in scheme.name:
                if farmer.is_oilseed_farmer or farmer.district in ['Sangli', 'Satara', 'Ratnagiri']:
                    score = 85
                    reason = "Perfect for oilseed cultivation in your region"
            
            # Soil Health Card - all farmers
            elif "soil" in scheme.name.lower():
                score = 80
                reason = "Optimize your land productivity with soil testing"
            
            # Crop Insurance - all farmers
            elif "insurance" in scheme.name.lower() or "PMFBY" in scheme.name:
                score = 75
                reason = "Protect your crops from natural disasters"
            
            # Irrigation schemes - land area dependent
            elif "irrigation" in scheme.name.lower() or "Per Drop" in scheme.name:
                if farmer.total_land_area_hectares >= 0.5:
                    score = 70
                    reason = "Improve water efficiency on your farm"
            
            # Dairy/Livestock - complementary income
            elif "dairy" in scheme.name.lower() or "livestock" in scheme.name.lower():
                score = 65
                reason = "Diversify income through livestock farming"
            
            # Mechanization - medium/large farmers
            elif "mechanization" in scheme.name.lower() or "SMAM" in scheme.name:
                if farmer.total_land_area_hectares >= 1.0:
                    score = 70
                    reason = "Reduce farming costs with modern equipment"
            
            # Horticulture - alternative crops
            elif "horticulture" in scheme.name.lower() or "MIDH" in scheme.name:
                score = 60
                reason = "High-value crop option for your land"
            
            # Employment/MGNREGA - additional income
            elif "employment" in scheme.name.lower() or "MGNREGA" in scheme.name:
                score = 55
                reason = "Additional guaranteed income source"
            
            # Natural Farming - sustainability
            elif "natural" in scheme.name.lower():
                score = 50
                reason = "Organic farming with government support"
            
            # Credit schemes
            elif "credit" in scheme.name.lower() or "KCC" in scheme.name:
                score = 75
                reason = "Easy agricultural credit at low rates"
            
            # Technology/Training
            elif "technology" in scheme.name.lower() or "ATMA" in scheme.name:
                score = 60
                reason = "Learn modern farming techniques free"
            
            # Market access schemes
            elif "market" in scheme.name.lower() or "e-NAM" in scheme.name:
                score = 70
                reason = "Direct market access for better prices"
            
            # Infrastructure
            elif "infrastructure" in scheme.name.lower() or "AIF" in scheme.name:
                if farmer.total_land_area_hectares >= 2.0:
                    score = 65
                    reason = "Build farm infrastructure"
            
            # Disability-based schemes
            if farmer.is_physically_handicapped and "disabled" in scheme.description.lower():
                score += 20
                reason = "Special scheme for differently-abled farmers"
            
            # SC/ST schemes
            if farmer.caste_category in ['SC', 'ST']:
                if "SC" in scheme.description or "ST" in scheme.description or "scheduled" in scheme.description.lower():
                    score += 15
                    reason += " (SC/ST eligibility bonus)"
            
            if score > 0:
                scheme_scores.append({
                    'scheme': scheme,
                    'score': score,
                    'reason': reason
                })
        
        # Sort by score and get top 5
        top_schemes = sorted(scheme_scores, key=lambda x: x['score'], reverse=True)[:5]
        
        # Convert to response format
        recommendations = []
        for item in top_schemes:
            scheme = item['scheme']
            priority = 'high' if item['score'] >= 80 else 'medium' if item['score'] >= 60 else 'low'
            
            recommendations.append({
                'id': scheme.id,
                'name': scheme.name,
                'description': scheme.description,
                'benefit_amount': scheme.benefit_amount,
                'eligibility_criteria': scheme.eligibility_criteria,
                'focus_area': scheme.focus_area,
                'focus_color': scheme.focus_color,
                'external_link': scheme.external_link,
                'reason': item['reason'],
                'priority': priority,
                'match_percentage': item['score'],
                'ai_method': 'rule_based'
            })
        
        return recommendations
    
    except Exception as e:
        print(f"Rule-based recommendation error: {str(e)}")
        return None
