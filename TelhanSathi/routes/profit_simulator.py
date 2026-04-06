from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from extensions import db
from models import Farmer
from datetime import datetime
import sys
import os

profit_bp = Blueprint('profit', __name__, url_prefix='/profit')

# Import the ML profit simulator based on ARIMA
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from ml.profit_simulator_arima import get_profit_simulator
    simulator = get_profit_simulator()
    ML_AVAILABLE = simulator.model_available
    logger_msg = "[OK] ARIMA Profit Simulator loaded successfully"
except Exception as e:
    print(f"[WARNING] Profit Simulator not available - {str(e)}")
    print("   ML models may not be trained")
    ML_AVAILABLE = False
    simulator = None
    logger_msg = f"Profit Simulator Error: {str(e)}"

print(logger_msg)



def get_market_price(crop_name):
    """
    Return market prices for crops from oilseed parameters (₹/quintal).
    """
    price_map = {
        'Groundnut': 6100,
        'Linseed (Flaxseed)': 5500,
        'Mustard': 5200,
        'Sesame': 7200,
        'Soybean': 4650,
    }
    return price_map.get(crop_name, 5000)


@profit_bp.route('/simulator')
def simulator_page():
    if 'farmer_id_verified' not in session:
        return redirect(url_for('auth.login'))
    return render_template('profit_simulator.html')


@profit_bp.route('/api/init')
def api_init():
    """Return prefilled farmer data and available markets/commodities."""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    farmer = Farmer.query.filter_by(id=session['farmer_id_verified']).first()
    if not farmer:
        return jsonify({'error': 'Farmer not found'}), 404

    # Get available markets and commodities from simulator
    available_markets = simulator.get_available_markets() if ML_AVAILABLE and simulator else []
    available_commodities = simulator.get_available_commodities() if ML_AVAILABLE and simulator else []

    # Get current crop or default to Mustard
    current_crop = farmer.current_crops.split(',')[0] if farmer.current_crops else 'Mustard'
    if current_crop not in available_commodities:
        current_crop = available_commodities[0] if available_commodities else 'Mustard'
    
    # Convert hectares to acres for display
    area_acres = round((farmer.total_land_area_hectares or 0.5) * 2.471054, 2)
    
    # Extract state from farmer if available - find matching market
    market = farmer.district or (available_markets[0] if available_markets else 'Delhi')
    if market not in available_markets:
        market = available_markets[0] if available_markets else 'Delhi'
    
    harvest_month = farmer.harvest_date.strftime('%B') if farmer.harvest_date else 'October'

    return jsonify({
        'farmer': {
            'id': farmer.id,
            'name': farmer.name,
            'market': market,
            'state': farmer.state or 'Maharashtra',
            'district': farmer.district or 'Indore',
            'soil_type': farmer.soil_type or '',
            'water_type': farmer.water_type or 'Freshwater',
            'current_crop': current_crop,
            'area_in_acres': area_acres,
            'harvest_month': harvest_month
        },
        'available_markets': available_markets,
        'available_commodities': available_commodities,
        'selected_market': market,
        'selected_commodity': current_crop,
        'harvest_months': ['January', 'February', 'March', 'April', 'May', 'June', 
                           'July', 'August', 'September', 'October', 'November', 'December'],
        'ml_available': ML_AVAILABLE
    })


@profit_bp.route('/api/simulate', methods=['POST'])
def api_simulate():
    """
    Calculate profit using ARIMA-based price forecasts.
    """
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    if not ML_AVAILABLE or not simulator:
        return jsonify({
            'error': 'ML मॉडल उपलब्ध नहीं है',
            'details': 'कृपया सर्वर को रीस्टार्ट करें या डेटा सेट कॉन्फ़िगर करें'
        }), 503

    data = request.json or {}
    
    try:
        market = data.get('market', 'Delhi')
        commodity = data.get('commodity', 'Soybean')
        area_in_acres = float(data.get('area_in_acres', 1.0))
        harvest_month = data.get('harvest_month', 'October')
        custom_cost_per_acre = data.get('custom_cost_per_acre', None)
        
        # Convert custom cost to float if provided
        if custom_cost_per_acre is not None:
            custom_cost_per_acre = float(custom_cost_per_acre)
    except (ValueError, TypeError) as e:
        return jsonify({'error': 'अमान्य इनपुट', 'details': str(e)}), 400

    try:
        # Run profit simulation for 30 days with custom cost if provided
        result = simulator.simulate_profit_30days(
            market=market,
            commodity=commodity,
            area_acres=area_in_acres,
            custom_cost_per_acre=custom_cost_per_acre
        )
        
        if result['status'] == 'error':
            return jsonify({
                'error': 'पूर्वानुमान विफल',
                'details': result['message']
            }), 400
        
        # Format response for UI
        prediction = {
            'gross_revenue': result['revenue']['total_30days'],
            'total_cost': result['cost']['total_30days'],
            'net_profit': result['profit']['total_30days'],
            'profit_margin': f"{result['profit']['margin_percent']}%",
            'roi': f"{result['financial']['roi_percent']}%",
            'breakeven_months': result['financial']['breakeven_days'],
            'forecast_price': result['price']['average_forecast'],
            'monthly_profit': result['profit']['daily_average'] * 30,
            'price_current': result['price']['current'],
            'price_min': result['price']['minimum'],
            'price_max': result['price']['maximum'],
            'price_trend': result['price']['trend'],
            'model_used': 'ARIMA',
            'forecast_months': result['forecast_period_days'],
        }
        
        return jsonify({
            'crop_name': commodity,
            'market': market,
            'area_in_acres': area_in_acres,
            'soil_type': data.get('soil_type', ''),
            'water_type': data.get('water_type', 'Freshwater'),
            'harvest_month': harvest_month,
            'prediction': prediction,
            'ml_enabled': True
        })
        
    except ValueError as e:
        return jsonify({
            'error': 'डेटा उपलब्ध नहीं है',
            'details': f'{market} में {commodity} के लिए डेटा उपलब्ध नहीं है'
        }), 400
    except Exception as e:
        import traceback
        print(f"❌ Profit simulation error: {e}")
        traceback.print_exc()
        return jsonify({
            'error': 'पूर्वानुमान में त्रुटि',
            'details': str(e)
        }), 500


# ========== COMMODITY COMPARISON ROUTE ==========

@profit_bp.route('/api/compare-commodities', methods=['POST'])
def api_compare_commodities():
    """Compare profit potential across commodities in a market."""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    if not ML_AVAILABLE or not simulator:
        return jsonify({'error': 'ML models not available'}), 503

    data = request.json or {}
    market = data.get('market', 'Delhi')
    area_in_acres = float(data.get('area_in_acres', 1.0))

    try:
        result = simulator.compare_commodities(market, area_in_acres)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
