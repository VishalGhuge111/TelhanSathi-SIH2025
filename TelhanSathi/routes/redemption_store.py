"""
Redemption Store Routes
Manages gamified coin rewards and redemption offers for farmers.
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect
from datetime import datetime, timedelta
from extensions import db
from models import Farmer, CoinBalance, CoinTransaction, RedemptionOffer, FarmerRedemption
import random
import string
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

redemption_bp = Blueprint('redemption', __name__, url_prefix='/redemption')

# ===== UTILITY FUNCTIONS =====

def get_current_farmer():
    """Get the current logged-in farmer from session."""
    farmer_id_verified = session.get('farmer_id_verified')
    logger.debug(f"Session farmer_id_verified: {farmer_id_verified}")
    logger.debug(f"Session keys: {list(session.keys())}")
    
    if not farmer_id_verified:
        logger.warning("No farmer_id_verified in session")
        return None
    
    # farmer_id_verified is the farmer's UUID, not the farmer_id (12-digit)
    farmer = Farmer.query.get(farmer_id_verified)
    logger.debug(f"Farmer query result: {farmer}")
    return farmer

def ensure_coin_balance(farmer):
    """Ensure farmer has a coin balance record."""
    if not farmer.coin_balance:
        coin_balance = CoinBalance(farmer_id=farmer.id)
        db.session.add(coin_balance)
        db.session.commit()
    return farmer.coin_balance

def generate_redemption_code():
    """Generate a unique redemption code."""
    code = 'TS' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    # Ensure uniqueness
    while FarmerRedemption.query.filter_by(redemption_code=code).first():
        code = 'TS' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return code

def initialize_redemption_offers():
    """Initialize default redemption offers in database.
    
    NOTE: Offers are now seeded from backup_redemption_offers_hindi.json
    using seed_database.py script. This function is disabled to prevent
    re-initialization with English data.
    
    To seed offers, run:
        python seed_database.py
    """
    # Skip initialization - offers are loaded from database via seed_database.py
    return


# ===== ROUTE HANDLERS =====

@redemption_bp.route('/store', methods=['GET'])
def redemption_store():
    """Display the redemption store page."""
    logger.debug(f"Redemption store page - Session: {dict(session)}")
    
    farmer = get_current_farmer()
    if not farmer:
        logger.warning("No farmer found in redemption_store - redirecting to login")
        return redirect('/login')
    
    # Initialize coin balance if needed
    coin_balance = ensure_coin_balance(farmer)
    
    # Initialize default offers if needed
    initialize_redemption_offers()
    
    # Render store page
    return render_template('redemption_store.html', farmer=farmer, coin_balance=coin_balance)


@redemption_bp.route('/api/offers', methods=['GET'])
def get_offers():
    """API endpoint to get all redemption offers with filters."""
    logger.debug(f"Getting offers - Session: {dict(session)}")
    
    farmer = get_current_farmer()
    if not farmer:
        logger.warning("No farmer found in get_offers")
        return jsonify({'error': 'Unauthorized'}), 401
    
    coin_balance = ensure_coin_balance(farmer)
    category = request.args.get('category')
    
    query = RedemptionOffer.query.filter_by(is_active=True)
    
    if category and category != 'all':
        query = query.filter_by(category=category)
    
    offers = query.order_by(RedemptionOffer.created_at).all()
    
    return jsonify({
        'offers': [offer.to_dict() for offer in offers],
        'available_coins': coin_balance.available_coins,
        'total_coins': coin_balance.total_coins
    })


@redemption_bp.route('/api/balance', methods=['GET'])
def get_coin_balance():
    """Get current farmer's coin balance."""
    logger.debug(f"Getting coin balance - Session: {dict(session)}")
    
    farmer = get_current_farmer()
    if not farmer:
        logger.warning("No farmer found in get_coin_balance")
        return jsonify({'error': 'Unauthorized'}), 401
    
    logger.debug(f"Found farmer: {farmer.farmer_id}")
    coin_balance = ensure_coin_balance(farmer)
    
    return jsonify({
        'total_coins': coin_balance.total_coins,
        'available_coins': coin_balance.available_coins,
        'redeemed_coins': coin_balance.redeemed_coins,
        'farmer_name': farmer.name,
        'farmer_id': farmer.farmer_id
    })


@redemption_bp.route('/api/best-offer', methods=['GET'])
def get_best_offer():
    """Get the best affordable offer for the farmer."""
    logger.debug(f"Getting best offer - Session: {dict(session)}")
    
    farmer = get_current_farmer()
    if not farmer:
        logger.warning("No farmer found in get_best_offer")
        return jsonify({'error': 'Unauthorized'}), 401
    
    coin_balance = ensure_coin_balance(farmer)
    available_coins = coin_balance.available_coins
    
    # Get all active offers sorted by coin cost (ascending)
    offers = RedemptionOffer.query.filter_by(is_active=True).order_by(RedemptionOffer.coin_cost).all()
    
    if not offers:
        return jsonify({
            'has_offer': False,
            'available_coins': available_coins,
            'message': 'No offers available'
        })
    
    # Find best offer within budget
    best_offer = None
    for offer in offers:
        if available_coins >= offer.coin_cost:
            best_offer = offer
            break  # Get the cheapest one they can afford
    
    if best_offer:
        return jsonify({
            'has_offer': True,
            'available_coins': available_coins,
            'offer': best_offer.to_dict(),
            'can_redeem': True
        })
    else:
        # No offer within budget, recommend the cheapest one
        cheapest_offer = offers[0]
        coins_needed = cheapest_offer.coin_cost - available_coins
        
        return jsonify({
            'has_offer': True,
            'available_coins': available_coins,
            'offer': cheapest_offer.to_dict(),
            'can_redeem': False,
            'coins_needed': coins_needed,
            'message': f'Earn {coins_needed} more coins to redeem this offer!'
        })


@redemption_bp.route('/api/redeem', methods=['POST'])
def redeem_offer():
    """Redeem an offer using coins."""
    logger.debug(f"Redeem offer - Session: {dict(session)}")
    
    farmer = get_current_farmer()
    if not farmer:
        logger.warning("No farmer found in redeem_offer")
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    offer_id = data.get('offer_id')
    
    # Validate offer exists
    offer = RedemptionOffer.query.get(offer_id)
    if not offer:
        return jsonify({'error': 'Offer not found'}), 404
    
    if not offer.is_active:
        return jsonify({'error': 'Offer is no longer active'}), 400
    
    # Check stock availability
    if offer.stock_limit and offer.stock_redeemed >= offer.stock_limit:
        return jsonify({'error': 'Out of stock'}), 400
    
    # Get coin balance
    coin_balance = ensure_coin_balance(farmer)
    
    # Check if farmer has enough coins
    if coin_balance.available_coins < offer.coin_cost:
        return jsonify({'error': 'Insufficient coins', 'required': offer.coin_cost, 'available': coin_balance.available_coins}), 400
    
    try:
        # Create redemption record
        redemption_code = generate_redemption_code()
        expires_at = datetime.utcnow() + timedelta(days=offer.validity_days)
        
        redemption = FarmerRedemption(
            farmer_id=farmer.id,
            offer_id=offer_id,
            coins_spent=offer.coin_cost,
            redemption_code=redemption_code,
            expires_at=expires_at,
            status='active'
        )
        
        # Update coin balance
        coin_balance.available_coins -= offer.coin_cost
        coin_balance.redeemed_coins += offer.coin_cost
        coin_balance.updated_at = datetime.utcnow()
        
        # Update offer stock
        offer.stock_redeemed += 1
        
        # Record transaction
        transaction = CoinTransaction(
            coin_balance_id=coin_balance.id,
            transaction_type='redeemed',
            amount=offer.coin_cost,
            reason=f'Redeemed: {offer.title}',
            related_type='redemption_offer',
            related_id=offer_id
        )
        
        db.session.add(redemption)
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'redemption_code': redemption_code,
            'offer_title': offer.title,
            'expires_at': expires_at.isoformat(),
            'remaining_coins': coin_balance.available_coins
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@redemption_bp.route('/api/my-redemptions', methods=['GET'])
def get_my_redemptions():
    """Get farmer's redemption history."""
    logger.debug(f"Getting my redemptions - Session: {dict(session)}")
    
    farmer = get_current_farmer()
    if not farmer:
        logger.warning("No farmer found in get_my_redemptions")
        return jsonify({'error': 'Unauthorized'}), 401
    
    status = request.args.get('status', 'all')
    
    query = FarmerRedemption.query.filter_by(farmer_id=farmer.id)
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    redemptions = query.order_by(FarmerRedemption.redeemed_at.desc()).all()
    
    return jsonify({
        'redemptions': [redemption.to_dict() for redemption in redemptions]
    })


@redemption_bp.route('/my-orders', methods=['GET'])
def my_redemptions():
    """Display farmer's redemption history page."""
    farmer = get_current_farmer()
    if not farmer:
        return redirect('/login')
    
    coin_balance = ensure_coin_balance(farmer)
    
    return render_template('redemption_orders.html', farmer=farmer, coin_balance=coin_balance)


@redemption_bp.route('/api/add-coins', methods=['POST'])
def add_coins_manual():
    """Admin endpoint to add coins to farmer (for testing/admin purposes)."""
    farmer = get_current_farmer()
    if not farmer:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    amount = data.get('amount', 0)
    reason = data.get('reason', 'Manual Addition')
    
    if amount <= 0:
        return jsonify({'error': 'Invalid amount'}), 400
    
    try:
        coin_balance = ensure_coin_balance(farmer)
        
        coin_balance.total_coins += amount
        coin_balance.available_coins += amount
        coin_balance.updated_at = datetime.utcnow()
        
        transaction = CoinTransaction(
            coin_balance_id=coin_balance.id,
            transaction_type='earned',
            amount=amount,
            reason=reason
        )
        
        farmer.coins_earned += amount
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'total_coins': coin_balance.total_coins,
            'available_coins': coin_balance.available_coins
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
