from flask import Blueprint, render_template, jsonify, session, request
from datetime import datetime, timedelta
import random
import requests
import os
import json
from models import Farmer, WeatherRecommendation
from extensions import db

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

weather_bp = Blueprint('weather', __name__, url_prefix='/weather')


@weather_bp.route('/')
def dashboard():
    # simple page; JS will fetch forecast
    if 'farmer_id_verified' not in session:
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    return render_template('weather.html')


def generate_forecast_for_location(district=None, lat=None, lon=None, days=7):
    """
    Stub weather forecast generator.
    Uses deterministic randomness seeded from district or lat/lon to create plausible day forecasts.
    Returns a list of days with date, summary, temp_min, temp_max, precipitation_mm, wind_kmh.
    """
    seed_val = 0
    if district:
        seed_val = sum(ord(c) for c in district)
    elif lat and lon:
        seed_val = int((abs(lat) + abs(lon)) * 1000)
    else:
        seed_val = int(datetime.utcnow().timestamp())

    rnd = random.Random(seed_val)
    out = []
    today = datetime.utcnow().date()
    for i in range(days):
        d = today + timedelta(days=i)
        # base temps vary mildly
        base = 25 + (rnd.random() * 8 - 2)
        tmax = round(base + rnd.uniform(2, 6), 1)
        tmin = round(base - rnd.uniform(2, 6), 1)
        precip_chance = rnd.random()
        if precip_chance > 0.8:
            summary = 'Heavy rain'
            precip = round(rnd.uniform(10, 60),1)
        elif precip_chance > 0.6:
            summary = 'Light rain'
            precip = round(rnd.uniform(1, 10),1)
        elif precip_chance > 0.4:
            summary = 'Cloudy'
            precip = 0.0
        else:
            summary = 'Sunny'
            precip = 0.0
        wind = round(rnd.uniform(5, 25),1)
        out.append({
            'date': d.isoformat(),
            'summary': summary,
            'temp_min': tmin,
            'temp_max': tmax,
            'precip_mm': precip,
            'wind_kmh': wind
        })
    return out


@weather_bp.route('/api/forecast')
def api_forecast():
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    farmer_id = session['farmer_id_verified']
    farmer = Farmer.query.filter_by(id=farmer_id).first()
    
    # Default to India's approximate center if no farmer location
    lat, lon = 20.5937, 78.9629
    location_name = 'India'
    
    if farmer:
        # Map common Indian districts to approximate lat/lon
        district_coords = {
            'Maharashtra': (19.7515, 75.7139),
            'Karnataka': (15.3173, 75.7139),
            'Gujarat': (22.2587, 71.1924),
            'Punjab': (31.1471, 74.8722),
            'Haryana': (29.0588, 77.0745),
            'Uttar Pradesh': (26.8467, 80.9462),
            'Madhya Pradesh': (22.9375, 78.6553),
            'Bihar': (25.0961, 85.3131),
            'West Bengal': (24.3745, 88.2007),
            'Tamil Nadu': (11.1271, 79.2787),
            'Andhra Pradesh': (15.9129, 79.7400),
            'Telangana': (18.1124, 79.0193),
            'Rajasthan': (27.0238, 74.2179),
        }
        
        district = getattr(farmer, 'district', None)
        if district and district in district_coords:
            lat, lon = district_coords[district]
            location_name = district
        elif district:
            location_name = district
    
    try:
        # Use Open-Meteo free API (no key required)
        url = f"https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': lat,
            'longitude': lon,
            'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max',
            'timezone': 'Asia/Kolkata',
            'forecast_days': 7
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Parse the response
        forecast = []
        daily = data.get('daily', {})
        dates = daily.get('time', [])
        temps_max = daily.get('temperature_2m_max', [])
        temps_min = daily.get('temperature_2m_min', [])
        precip = daily.get('precipitation_sum', [])
        wind = daily.get('wind_speed_10m_max', [])
        weather_codes = daily.get('weather_code', [])
        
        for i in range(min(7, len(dates))):
            summary = get_weather_summary_from_code(weather_codes[i] if i < len(weather_codes) else 0)
            forecast.append({
                'date': dates[i] if i < len(dates) else '',
                'summary': summary,
                'temp_min': round(temps_min[i], 1) if i < len(temps_min) else 20,
                'temp_max': round(temps_max[i], 1) if i < len(temps_max) else 30,
                'precip_mm': round(precip[i], 1) if i < len(precip) else 0,
                'wind_kmh': round(wind[i] * 3.6, 1) if i < len(wind) else 10  # Convert m/s to km/h
            })
        
        return jsonify({'location': location_name, 'forecast': forecast})
    
    except Exception as e:
        print(f"Error fetching real weather: {e}")
        # Fallback to stub generator
        forecast = generate_forecast_for_location(district=location_name, days=7)
        return jsonify({'location': location_name, 'forecast': forecast})


def get_weather_summary_from_code(code):
    """
    Convert WMO weather code to summary string.
    Based on WMO codes: https://www.weatherapi.com/docs/
    """
    code = int(code)
    if code == 0:
        return 'Clear'
    elif code == 1 or code == 2:
        return 'Partly cloudy'
    elif code == 3:
        return 'Overcast'
    elif code == 45 or code == 48:
        return 'Foggy'
    elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        return 'Rainy'
    elif code in [71, 73, 75, 77, 85, 86]:
        return 'Snowy'
    elif code in [80, 81, 82]:
        return 'Rain showers'
    elif code in [85, 86]:
        return 'Snow showers'
    elif code in [95, 96, 99]:
        return 'Thunderstorm'
    else:
        return 'Cloudy'


# ======================== WEATHER AI RECOMMENDATION FUNCTIONS ========================

def _get_farmer_context(farmer):
    """Extract relevant farmer information for Gemini context"""
    return {
        'name': farmer.name,
        'state': farmer.state,
        'district': farmer.district,
        'taluka': farmer.taluka,
        'village': farmer.village,
        'land_area_hectares': farmer.total_land_area_hectares,
        'soil_type': farmer.soil_type,
        'current_crops': farmer.current_crops,
        'water_type': farmer.water_type,
        'is_oilseed_farmer': farmer.is_oilseed_farmer
    }


def _is_cache_valid(weather_rec):
    """Check if cached recommendation is still valid"""
    if not weather_rec:
        return False
    if not weather_rec.expires_at:
        return False
    return weather_rec.expires_at > datetime.utcnow()


def _get_gemini_weather_recommendations(farmer, forecast):
    """
    Get weather-based recommendations using Gemini API.
    Returns structured recommendations or None if API fails.
    """
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("[WEATHER] No GEMINI_API_KEY configured")
            return None
        
        # Build farmer and weather context
        farmer_context = _get_farmer_context(farmer)
        
        # Create detailed prompt for Gemini
        prompt = f"""
आप एक कृषि सलाहकार हैं जो भारतीय किसानों को फसल प्रबंधन और मौसम-आधारित खेती में विशेषज्ञ सलाह देते हैं।

किसान की जानकारी:
- नाम: {farmer_context.get('name', 'Unknown')}
- स्थान: {farmer_context.get('taluka', '')}, {farmer_context.get('district', '')}, {farmer_context.get('state', '')}
- भूमि क्षेत्र: {farmer_context.get('land_area_hectares', 0)} हेक्टेयर
- मिट्टी का प्रकार: {farmer_context.get('soil_type', 'निर्दिष्ट नहीं')}
- वर्तमान फसलें: {farmer_context.get('current_crops', 'निर्दिष्ट नहीं')}
- पानी का प्रकार: {farmer_context.get('water_type', 'निर्दिष्ट नहीं')}

7 दिन का मौसम पूर्वानुमान:
{json.dumps(forecast, indent=2)}

किसान के स्थान, फसलों, मिट्टी के प्रकार और आने वाले 7 दिन के मौसम पूर्वानुमान के आधार पर, हिंदी में कार्ययोग्य सिफारिशें प्रदान करें।

केवल वैध JSON प्रारूप में प्रतिक्रिया दें:

{{
    "critical_alerts": [
        {{"type": "पाला|अत्यधिक बारिश|सूखा|ओले|अत्यधिक गर्मी", "severity": "high|medium|low", "days": [1-7], "summary": "1-2 पंक्ति हिंदी में", "details": "विस्तृत व्याख्या हिंदी में", "action": "करने योग्य कदम"}}
    ],
    "irrigation_advice": {{
        "summary": "सिंचाई需दी है या नहीं (1-2 पंक्ति में हिंदी)",
        "details": "विस्तृत जानकारी हिंदी में",
        "needed": true/false,
        "timing": "तुरंत|अगले 3 दिन|अगले सप्ताह",
        "quantity_mm": संख्या
    }},
    "pest_alerts": [
        {{"pest": "कीट का नाम हिंदी में", "summary": "संक्षिप्त चेतावनी हिंदी में", "details": "विस्तृत जानकारी हिंदी में", "risk_level": "high|medium|low", "prevention": "रोकथाम के उपाय हिंदी में"}}
    ],
    "fertilizer_timing": {{
        "summary": "खाद के बारे में संक्षिप्त सुझाव हिंदी में", 
        "details": "विस्तृत जानकारी हिंदी में",
        "next_application_day": संख्या,
        "type": "नाइट्रोजन|पोटेशियम|फॉस्फोरस|मिश्रित",
        "quantity_kg_per_hectare": संख्या
    }},
    "weather_warnings": [
        {{"condition": "मौसम की स्थिति हिंदी में", "summary": "संक्षिप्त चेतावनी", "details": "विस्तृत विवरण हिंदी में", "timing": "समय अवधि"}}
    ],
    "seasonal_insights": {{
        "summary": "मौसमी सुझाव संक्षिप्त रूप में हिंदी में",
        "details": "विस्तृत जानकारी हिंदी में",
        "planting_window": "बुवाई का समय",
        "harvest_timeline": "कटाई का समय"
    }}
}}

महत्वपूर्ण निर्देश:
1. सभी पाठ हिंदी में हो
2. प्रत्येक सिफारिश में "summary" (1-2 पंक्ति) और "details" (विस्तृत जानकारी) हो
3. तेलहन फसलों (मूंगफली, सोयाबीन, सूरजमुखी) के लिए विशेष ध्यान दें
4. केवल वैध JSON प्रारूप वापस करें, कोई मार्कडाउन नहीं
"""
        
        # Call Gemini API
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            recommendations = json.loads(json_str)
            return {
                'success': True,
                'recommendations': recommendations,
                'ai_method': 'gemini'
            }
        else:
            print(f"[WEATHER] Could not extract JSON from Gemini response: {response_text[:200]}")
            return None
    
    except json.JSONDecodeError as e:
        print(f"[WEATHER] JSON parse error from Gemini: {e}")
        return None
    except Exception as e:
        print(f"[WEATHER] Gemini API error: {str(e)}")
        return None


def _get_rule_based_weather_recommendations(farmer, forecast):
    """Rule-based fallback recommendations (no API calls)"""
    try:
        recommendations = {
            'critical_alerts': [],
            'irrigation_advice': {},
            'pest_alerts': [],
            'fertilizer_timing': {},
            'weather_warnings': [],
            'seasonal_insights': {},
            'general_notes': 'Rule-based recommendations generated (AI unavailable)'
        }
        
        # Check for excessive rainfall
        total_rainfall = sum(day.get('precip_mm', 0) for day in forecast)
        if total_rainfall > 50:
            recommendations['critical_alerts'].append({
                'type': 'excessive_rain',
                'severity': 'high',
                'days': [i+1 for i, d in enumerate(forecast) if d.get('precip_mm', 0) > 10],
                'description': 'High rainfall forecast - risk of waterlogging',
                'action': 'Ensure adequate drainage and avoid irrigation'
            })
        
        # Irrigation advice based on rainfall
        if total_rainfall < 10:
            recommendations['irrigation_advice'] = {
                'needed': True,
                'timing': 'immediate',
                'quantity_mm': 20,
                'reason': 'Low rainfall forecast - irrigation recommended',
                'crop_specific_tips': {'default': 'Apply 20-25mm irrigation'}
            }
        
        # Generic pest alerts based on temperature
        avg_temp = sum(day.get('temp_max', 25) for day in forecast) / len(forecast) if forecast else 25
        if avg_temp > 30:
            recommendations['pest_alerts'].append({
                'pest': 'Various insects (high temperature stress)',
                'risk_level': 'medium',
                'reason': f'Average temperature forecast: {avg_temp:.1f}°C - favorable for pest development',
                'prevention': 'Monitor crops regularly, consider preventive spraying if needed'
            })
        
        # Fertilizer timing
        recommendations['fertilizer_timing'] = {
            'next_application_day': 3,
            'type': 'nitrogen',
            'quantity_kg_per_hectare': 50,
            'precautions': 'Apply before expected rainfall for better absorption',
            'crop_specific': {'default': 'Standard fertilizer schedule'}
        }
        
        recommendations['seasonal_insights'] = {
            'optimal_planting_window': 'Consult with local agricultural extension officer',
            'harvest_timeline': 'Monitor crop maturity indicators',
            'yield_optimization': 'Ensure timely irrigation and fertilizer application'
        }
        
        return {
            'success': True,
            'recommendations': recommendations,
            'ai_method': 'rule_based'
        }
    
    except Exception as e:
        print(f"[WEATHER] Rule-based recommendation error: {str(e)}")
        return None


def _get_weather_recommendations(farmer_id):
    """
    Main function to get weather recommendations with caching and fallback.
    Returns cached recommendations if valid, otherwise generates new ones via Gemini or rule-based.
    """
    try:
        farmer = Farmer.query.filter_by(id=farmer_id).first()
        if not farmer:
            return {'error': 'Farmer not found'}
        
        # Check for valid cached recommendation (less than 24 hours old)
        cached_rec = WeatherRecommendation.query.filter(
            WeatherRecommendation.farmer_id == farmer_id,
            WeatherRecommendation.expires_at > datetime.utcnow()
        ).order_by(WeatherRecommendation.created_at.desc()).first()
        
        if cached_rec and _is_cache_valid(cached_rec):
            return {
                'success': True,
                'recommendations': cached_rec.recommendations,
                'weather_data': cached_rec.weather_data,
                'ai_method': cached_rec.ai_method,
                'from_cache': True,
                'expires_at': cached_rec.expires_at.isoformat()
            }
        
        # Clear expired recommendations
        WeatherRecommendation.query.filter(
            WeatherRecommendation.farmer_id == farmer_id,
            WeatherRecommendation.expires_at <= datetime.utcnow()
        ).delete()
        db.session.commit()
        
        # Fetch current weather forecast
        location_name = farmer.district or 'India'
        
        # Get weather data (reuse existing api_forecast logic)
        try:
            district_coords = {
                'Maharashtra': (19.7515, 75.7139),
                'Karnataka': (15.3173, 75.7139),
                'Gujarat': (22.2587, 71.1924),
                'Punjab': (31.1471, 74.8722),
                'Haryana': (29.0588, 77.0745),
                'Uttar Pradesh': (26.8467, 80.9462),
                'Madhya Pradesh': (22.9375, 78.6553),
                'Bihar': (25.0961, 85.3131),
                'West Bengal': (24.3745, 88.2007),
                'Tamil Nadu': (11.1271, 79.2787),
                'Andhra Pradesh': (15.9129, 79.7400),
                'Telangana': (18.1124, 79.0193),
                'Rajasthan': (27.0238, 74.2179),
            }
            
            lat, lon = 20.5937, 78.9629  # Default (India center)
            if farmer.district and farmer.district in district_coords:
                lat, lon = district_coords[farmer.district]
            
            url = f"https://api.open-meteo.com/v1/forecast"
            params = {
                'latitude': lat,
                'longitude': lon,
                'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max',
                'timezone': 'Asia/Kolkata',
                'forecast_days': 7
            }
            
            weather_response = requests.get(url, params=params, timeout=5)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            # Parse weather
            forecast = []
            daily = weather_data.get('daily', {})
            dates = daily.get('time', [])
            temps_max = daily.get('temperature_2m_max', [])
            temps_min = daily.get('temperature_2m_min', [])
            precip = daily.get('precipitation_sum', [])
            wind = daily.get('wind_speed_10m_max', [])
            weather_codes = daily.get('weather_code', [])
            
            for i in range(min(7, len(dates))):
                summary = get_weather_summary_from_code(weather_codes[i] if i < len(weather_codes) else 0)
                forecast.append({
                    'date': dates[i] if i < len(dates) else '',
                    'summary': summary,
                    'temp_min': round(temps_min[i], 1) if i < len(temps_min) else 20,
                    'temp_max': round(temps_max[i], 1) if i < len(temps_max) else 30,
                    'precip_mm': round(precip[i], 1) if i < len(precip) else 0,
                    'wind_kmh': round(wind[i] * 3.6, 1) if i < len(wind) else 10
                })
        except Exception as e:
            print(f"[WEATHER] Error fetching forecast: {e}")
            forecast = generate_forecast_for_location(district=location_name, days=7)
        
        # Try Gemini API first
        recommendations_result = None
        if GEMINI_AVAILABLE:
            recommendations_result = _get_gemini_weather_recommendations(farmer, forecast)
        
        # Fallback to rule-based if Gemini unavailable/failed
        if not recommendations_result:
            recommendations_result = _get_rule_based_weather_recommendations(farmer, forecast)
        
        if recommendations_result and recommendations_result.get('success'):
            # Cache the recommendations
            expiry_time = datetime.utcnow() + timedelta(hours=24)
            
            weather_rec = WeatherRecommendation(
                farmer_id=farmer_id,
                weather_data=forecast,
                recommendations=recommendations_result['recommendations'],
                ai_method=recommendations_result['ai_method'],
                expires_at=expiry_time
            )
            db.session.add(weather_rec)
            db.session.commit()
            
            return {
                'success': True,
                'recommendations': recommendations_result['recommendations'],
                'weather_data': forecast,
                'ai_method': recommendations_result['ai_method'],
                'from_cache': False,
                'expires_at': expiry_time.isoformat()
            }
        
        return {'error': 'Could not generate recommendations', 'success': False}
    
    except Exception as e:
        print(f"[WEATHER] Error in _get_weather_recommendations: {str(e)}")
        return {'error': str(e), 'success': False}


# ======================== API ENDPOINTS ========================

@weather_bp.route('/api/recommendations')
def api_weather_recommendations():
    """Get AI-powered weather-based recommendations with caching"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    farmer_id = session['farmer_id_verified']
    result = _get_weather_recommendations(farmer_id)
    
    if result.get('success'):
        # Store recommendations in session for detail page access
        session['recommendations'] = result['recommendations']
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@weather_bp.route('/api/refresh', methods=['POST'])
def api_refresh_recommendations():
    """Force refresh: clear cache and regenerate recommendations"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    farmer_id = session['farmer_id_verified']
    
    try:
        # Delete all existing recommendations for this farmer
        WeatherRecommendation.query.filter_by(farmer_id=farmer_id).delete()
        db.session.commit()
        
        # Generate fresh recommendations
        result = _get_weather_recommendations(farmer_id)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Recommendations refreshed successfully',
                'recommendations': result['recommendations'],
                'weather_data': result['weather_data'],
                'ai_method': result['ai_method'],
                'expires_at': result['expires_at']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate recommendations')
            }), 500
    
    except Exception as e:
        print(f"[WEATHER] Error in refresh: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@weather_bp.route('/api/ask-followup', methods=['POST'])
def api_ask_followup():
    """Interactive chat: ask follow-up questions to Gemini about recommendations"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        farmer_id = session['farmer_id_verified']
        data = request.get_json() or {}
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        if not GEMINI_AVAILABLE:
            return jsonify({
                'error': 'AI chat unavailable',
                'message': 'Gemini API is not configured'
            }), 503
        
        # Get the latest recommendation for context
        weather_rec = WeatherRecommendation.query.filter_by(
            farmer_id=farmer_id
        ).order_by(WeatherRecommendation.created_at.desc()).first()
        
        if not weather_rec or not weather_rec.recommendations:
            return jsonify({
                'error': 'No recommendations found',
                'message': 'Please generate recommendations first'
            }), 404
        
        farmer = Farmer.query.filter_by(id=farmer_id).first()
        
        # Build context for follow-up
        context_prompt = f"""
You are an agricultural advisor helping a farmer understand weather-based crop management.

FARMER CONTEXT:
- Name: {farmer.name if farmer else 'Unknown'}
- Location: {farmer.district if farmer else 'Unknown'}, {farmer.state if farmer else 'Unknown'}
- Crops: {farmer.current_crops if farmer else 'Unknown'}
- Soil: {farmer.soil_type if farmer else 'Unknown'}

PREVIOUS RECOMMENDATIONS:
{json.dumps(weather_rec.recommendations, indent=2)}

FARMER'S QUESTION: {question}

Provide a brief, helpful answer (2-3 sentences maximum) related to the above recommendations and the farmer's situation.
Be direct and actionable. Do not provide long explanations or multiple paragraphs.
"""
        
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            response = model.generate_content(context_prompt)
            answer = response.text.strip()
            
            # Store chat context for future reference (in this session)
            if not weather_rec.chat_context:
                weather_rec.chat_context = []
            
            weather_rec.chat_context.append({
                'role': 'user',
                'content': question
            })
            weather_rec.chat_context.append({
                'role': 'assistant',
                'content': answer
            })
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'question': question,
                'answer': answer,
                'context': 'Based on your current weather forecast and recommendations'
            }), 200
        
        except Exception as e:
            print(f"[WEATHER] Gemini chat error: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Failed to get response: {str(e)}'
            }), 500
    
    except Exception as e:
        print(f"[WEATHER] Follow-up error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ======================== DETAILS PAGE ROUTE ========================

@weather_bp.route('/details/<detail_type>')
def details_page(detail_type):
    """Display detailed information for a specific recommendation"""
    if 'farmer_id_verified' not in session:
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    farmer_id = session.get('farmer_id_verified')
    farmer = Farmer.query.filter_by(id=farmer_id).first()
    
    # Get recommendations from session or API
    if 'recommendations' not in session:
        result = _get_weather_recommendations(farmer_id)
        if not result.get('success'):
            return render_template('weather_details.html', 
                                   error='सिफारिशें लोड नहीं कर सकते',
                                   farmer_name=farmer.name if farmer else 'किसान')
        session['recommendations'] = result['recommendations']
    
    recommendations = session.get('recommendations', {})
    
    # Extract details based on type
    detail_data = None
    title = ''
    
    if detail_type == 'irrigation':
        detail_data = recommendations.get('irrigation_advice', {})
        title = '💧 सिंचाई सलाह'
    
    elif detail_type == 'pest':
        detail_data = recommendations.get('pest_alerts', [])
        if detail_data and isinstance(detail_data, list):
            detail_data = detail_data[0] if detail_data else {}
        title = '🐛 कीट नियंत्रण'
    
    elif detail_type == 'fertilizer':
        detail_data = recommendations.get('fertilizer_timing', {})
        title = '🌾 खाद का समय'
    
    elif detail_type == 'weather':
        detail_data = recommendations.get('weather_warnings', [])
        if detail_data and isinstance(detail_data, list):
            detail_data = detail_data[0] if detail_data else {}
        title = '⚠️ मौसम चेतावनी'
    
    elif detail_type == 'seasonal':
        detail_data = recommendations.get('seasonal_insights', {})
        title = '📈 मौसमी सुझाव'
    
    elif detail_type == 'alerts':
        detail_data = recommendations.get('critical_alerts', [])
        title = '🚨 गंभीर चेतावनियां'
    
    return render_template('weather_details.html',
                           detail_type=detail_type,
                           title=title,
                           detail_data=detail_data,
                           farmer_name=farmer.name if farmer else 'किसान')
