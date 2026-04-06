"""
Crop Economics & Market Pricing Routes
Provides mock market pricing data for oilseeds with simulated loading
"""

from flask import Blueprint, render_template, jsonify, session, request
from functools import wraps
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from extensions import db

crop_economics_bp = Blueprint('crop_economics', __name__, url_prefix='/crop-economics')

# Using mock data for development (real API integration can be added later)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'farmer_id_verified' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Common oilseeds in India (mapped to government API commodity names)
OILSEEDS = {
    'soybean': {'name': 'Soybean', 'unit': 'per quintal', 'icon': '🫘', 'api_name': 'Soyabean'},
    'sesame': {'name': 'Sesame', 'unit': 'per kg', 'icon': '🌾', 'api_name': 'Sesame'},
    'mustard': {'name': 'Mustard', 'unit': 'per quintal', 'icon': '🌾', 'api_name': 'Mustard'},
    'linseed': {'name': 'Linseed (Flaxseed)', 'unit': 'per quintal', 'icon': '🌾', 'api_name': 'Linseed'},
    'groundnut': {'name': 'Groundnut', 'unit': 'per quintal', 'icon': '🫘', 'api_name': 'Groundnut'},
}

# Major markets for oilseed trading in India
MARKETS = {
    'Chennai': 'Chennai',
    'Delhi': 'Delhi',
    'Indore': 'Indore',
    'Mumbai': 'Mumbai',
    'Surat': 'Surat',
}

def fetch_live_prices_from_api(commodity_name, market_filter=None):
    """
    Fetch live prices - returns mock data with simulated loading delay
    This provides a realistic experience while avoiding API timeouts
    """
    import time
    
    # Simulate API latency with small delay (500-1000ms)
    time.sleep(0.5)
    
    # Return mock data for demonstration
    print(f"Loading mock data for {commodity_name}")
    return get_mock_prices(commodity_name, market_filter=market_filter)


def get_mock_prices(commodity_name, market_filter=None):
    """Return mock prices for demonstration, optionally filtered by market"""
    import random
    base_prices = {
        'Soyabean': 5500,
        'Soybean': 5500,
        'Sesame': 8200,
        'Mustard': 6200,
        'Linseed': 5800,
        'Groundnut': 7400,
    }
    
    base = base_prices.get(commodity_name, 5000)
    
    # Main markets for oilseed trading
    all_markets = list(MARKETS.values())
    
    # Select markets based on market filter
    if market_filter:
        market_lower = market_filter.lower()
        # Find matching market
        selected_markets = [m for m in all_markets if m.lower() == market_lower]
        # If no exact match, use the provided market name
        if not selected_markets:
            selected_markets = [market_filter]
    else:
        # If no market filter, use all markets
        selected_markets = all_markets
    
    prices = []
    for market in selected_markets[:6]:
        variation = random.randint(-500, 500)
        prices.append({
            'price': round(base + variation, 2),
            'market': market,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'min_price': round(base - 300, 2),
            'max_price': round(base + 300, 2)
        })
    
    return prices

@crop_economics_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Serve crop economics dashboard page"""
    return render_template('crop_economics.html', oilseeds=OILSEEDS)

@crop_economics_bp.route('/api/markets', methods=['GET'])
@login_required
def get_markets():
    """
    Get list of all available markets for oilseed trading data
    Returns hardcoded list of major oilseed markets in India
    """
    try:
        # Return known oilseed trading markets in India
        market_list = list(MARKETS.values())
        return jsonify({'markets': market_list})
    except Exception as e:
        print(f"Error fetching markets: {str(e)}")
        # Return default markets on error
        market_list = list(MARKETS.values())
        return jsonify({'markets': market_list})

@crop_economics_bp.route('/api/prices', methods=['GET'])
@login_required
def get_prices():
    """
    Get live prices for all oilseeds (mock data with simulated loading)
    Can filter by market using ?market=MARKET parameter
    Returns: {crop_name: {average: price, count: num_markets, max: price, min: price, markets: [...]}}
    """
    market_filter = request.args.get('market', None)
    prices = {}
    
    for crop_key, crop_info in OILSEEDS.items():
        # Fetch mock prices with simulated loading delay
        api_prices = fetch_live_prices_from_api(crop_info['api_name'], market_filter=market_filter)
        
        if api_prices:
            # Calculate statistics
            price_values = [p['price'] for p in api_prices if p['price'] > 0]
            
            if price_values:
                avg_price = sum(price_values) / len(price_values)
                max_price = max(price_values)
                min_price = min(price_values)
                
                prices[crop_key] = {
                    'crop_name': crop_info['name'],
                    'average': round(avg_price, 2),
                    'max': round(max_price, 2),
                    'min': round(min_price, 2),
                    'count': len(api_prices),
                    'unit': crop_info['unit'],
                    'icon': crop_info['icon'],
                    'trend': 'live',
                    'source': 'Mock Data',
                    'markets': api_prices[:10],  # Top 10 markets
                    'market_filtered': market_filter is not None
                }
            else:
                prices[crop_key] = get_empty_price(crop_info)
        else:
            prices[crop_key] = get_empty_price(crop_info)
    
    return jsonify(prices)



def get_empty_price(crop_info):
    """Return empty price structure when no data available"""
    return {
        'crop_name': crop_info['name'],
        'average': 0,
        'max': 0,
        'min': 0,
        'count': 0,
        'unit': crop_info['unit'],
        'icon': crop_info['icon'],
        'trend': 'no_data',
        'source': 'Mock Data',
        'markets': []
    }

def get_mock_price_history(crop_key, days=180):
    """Generate mock monthly historical price data for demonstration (last 12 months)"""
    import random
    from dateutil.relativedelta import relativedelta
    
    base_prices = {
        'soybean': 5500,
        'mustard': 6200,
        'groundnut': 7400,
        'sunflower': 6800,
        'safflower': 4900,
        'sesame': 8200,
        'coconut': 4500
    }
    
    base_price = base_prices.get(crop_key, 5000)
    history = []
    today = datetime.now()
    
    # Generate last 12 months of data
    for month_offset in range(11, -1, -1):
        # Go back month_offset months from today
        month_date = today - relativedelta(months=month_offset)
        month_date = month_date.replace(day=1)
        
        # Monthly price with trend and variation
        trend = (11 - month_offset) * 30  # Gradual price increase
        variation = random.gauss(0, 300)
        price = max(base_price + trend + variation, 1500)
        
        history.append({
            'date': month_date.strftime('%Y-%m-01'),
            'month': month_date.strftime('%b %Y'),
            'price': round(price, 2),
            'count': random.randint(10, 25)  # Number of markets reporting
        })
    
    return history


@crop_economics_bp.route('/api/price-history/<crop>', methods=['GET'])
@login_required
def get_price_history(crop):
    """
    Get market price history for a crop (last 6 months)
    Uses mock data for demonstration
    """
    crop_lower = crop.lower()
    
    if crop_lower not in OILSEEDS:
        return jsonify({'error': 'Crop not found'}), 404
    
    crop_info = OILSEEDS[crop_lower]
    
    # Generate mock historical data for last 180 days
    history = get_mock_price_history(crop_lower, days=180)
    
    return jsonify({
        'crop': crop_info['name'],
        'history': history,
        'source': 'Mock Data (Demo)'
    })

@crop_economics_bp.route('/api/comparison', methods=['GET'])
@login_required
def get_comparison():
    """
    Get live price comparison across multiple crops (mock data with simulated loading)
    Can filter by market using ?market=MARKET parameter
    """
    market_filter = request.args.get('market', None)
    comparison = []
    
    for crop_key, crop_info in OILSEEDS.items():
        api_prices = fetch_live_prices_from_api(crop_info['api_name'], market_filter=market_filter)
        
        if api_prices:
            price_values = [p['price'] for p in api_prices if p['price'] > 0]
            if price_values:
                avg_price = sum(price_values) / len(price_values)
                comparison.append({
                    'crop': crop_info['name'],
                    'price': round(avg_price, 2),
                    'icon': crop_info['icon'],
                    'count': len(api_prices)
                })
    
    return jsonify(comparison)

@crop_economics_bp.route('/api/top-crops', methods=['GET'])
@login_required
def get_top_crops():
    """
    Get top oilseeds by current market activity (mock data with simulated loading)
    Can filter by market using ?market=MARKET parameter
    """
    market_filter = request.args.get('market', None)
    crop_data = []
    
    for crop_key, crop_info in OILSEEDS.items():
        api_prices = fetch_live_prices_from_api(crop_info['api_name'], market_filter=market_filter)
        
        if api_prices:
            price_values = [p['price'] for p in api_prices if p['price'] > 0]
            if price_values:
                avg_price = sum(price_values) / len(price_values)
                crop_data.append({
                    'name': crop_info['name'],
                    'listings': len(api_prices),
                    'icon': crop_info['icon'],
                    'price': round(avg_price, 2)
                })
    
    # Sort by number of markets/listings and return top 5
    top_crops = sorted(crop_data, key=lambda x: x['listings'], reverse=True)[:5]
    
    return jsonify(top_crops)

@crop_economics_bp.route('/api/market-details/<crop>', methods=['GET'])
@login_required
def get_market_details(crop):
    """
    Get detailed price information across all markets for a crop (mock data)
    Can filter by market using ?market=MARKET parameter
    """
    crop_lower = crop.lower()
    market_filter = request.args.get('market', None)
    
    if crop_lower not in OILSEEDS:
        return jsonify({'error': 'Crop not found'}), 404
    
    crop_info = OILSEEDS[crop_lower]
    api_prices = fetch_live_prices_from_api(crop_info['api_name'], market_filter=market_filter)
    
    if not api_prices:
        return jsonify({
            'crop': crop_info['name'],
            'markets': [],
            'message': 'No market data available'
        }), 200
    
    # Sort by price (highest first)
    sorted_markets = sorted(api_prices, key=lambda x: x['price'], reverse=True)
    
    return jsonify({
        'crop': crop_info['name'],
        'total_markets': len(api_prices),
        'markets': sorted_markets,
        'source': 'Mock Data'
    })

