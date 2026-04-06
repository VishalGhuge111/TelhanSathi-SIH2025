"""
Real-Time Bidding System (NILAMI) for Oilseed Harvest
Provides auction management, bidding, and transaction handling
Farmer-side functionality
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from extensions import db
from models import Farmer
from models_marketplace_keep import Auction, Bid, CounterOffer, AuctionNotification, Buyer
from datetime import datetime, timedelta, date
import uuid
import os
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest

bidding_bp = Blueprint('bidding', __name__, url_prefix='/bidding')


# ==================== FARMER-SIDE ENDPOINTS ====================

@bidding_bp.route('/farmer/dashboard')
def farmer_dashboard():
    """Farmer's main bidding dashboard"""
    if 'farmer_id_verified' not in session:
        return redirect(url_for('auth.login'))
    
    farmer_id = session['farmer_id_verified']
    farmer = Farmer.query.get(farmer_id)
    
    if not farmer:
        return redirect(url_for('auth.login'))
    
    return render_template('farmer_auction_dashboard.html', farmer=farmer)


@bidding_bp.route('/farmer/create-auction', methods=['GET', 'POST'])
def create_auction():
    """Create a new auction for oilseed harvest"""
    if 'farmer_id_verified' not in session:
        return redirect(url_for('auth.login'))
    
    farmer_id = session['farmer_id_verified']
    
    if request.method == 'GET':
        farmer = Farmer.query.get(farmer_id)
        return render_template('farmer_create_auction.html', farmer=farmer)
    
    if request.method == 'POST':
        try:
            # Handle both FormData (with files) and JSON
            if request.is_json:
                data = request.get_json()
                photo_paths = {}
            else:
                data = request.form.to_dict()
                photo_paths = {}
                
                # Create uploads directory if it doesn't exist
                uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'auctions')
                os.makedirs(uploads_dir, exist_ok=True)
                
                # Handle photo uploads
                for i in range(1, 5):
                    file_key = f'photo{i}'
                    if file_key in request.files:
                        file = request.files[file_key]
                        if file and file.filename != '':
                            try:
                                filename = secure_filename(file.filename)
                                unique_filename = f"{uuid.uuid4()}_{filename}"
                                filepath = os.path.join(uploads_dir, unique_filename)
                                file.save(filepath)
                                # Store relative path for database
                                photo_paths[f'photo{i}_path'] = f'/static/uploads/auctions/{unique_filename}'
                            except Exception as e:
                                print(f"Error saving photo {i}: {str(e)}")
            
            # Validate required fields
            required_fields = ['crop_name', 'quantity_quintals', 'base_price', 'duration_hours', 'location', 'district']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400
            
            # Create auction
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(hours=int(data['duration_hours']))
            
            # Convert harvest_date string to date object if provided
            harvest_date = None
            if data.get('harvest_date'):
                try:
                    harvest_date_str = data['harvest_date']
                    if isinstance(harvest_date_str, str):
                        harvest_date = datetime.strptime(harvest_date_str, '%Y-%m-%d').date()
                    else:
                        harvest_date = harvest_date_str
                except:
                    harvest_date = None
            
            auction = Auction(
                id=str(uuid.uuid4()),
                farmer_id=farmer_id,
                crop_name=data['crop_name'],
                quantity_quintals=float(data['quantity_quintals']),
                quality_grade=data.get('quality_grade', 'Standard'),
                base_price_per_quintal=float(data['base_price']),
                minimum_bid_increment=float(data.get('minimum_bid_increment', 50)),
                start_time=start_time,
                end_time=end_time,
                location=data['location'],
                district=data['district'],
                state=data.get('state', 'Maharashtra'),
                description=data.get('description', ''),
                harvest_date=harvest_date,
                storage_location=data.get('storage_location', ''),
                status='active',
                current_highest_bid=float(data['base_price']),
                photo1_path=photo_paths.get('photo1_path'),
                photo2_path=photo_paths.get('photo2_path'),
                photo3_path=photo_paths.get('photo3_path'),
                photo4_path=photo_paths.get('photo4_path')
            )
            
            db.session.add(auction)
            db.session.commit()
            
            # 🔴 BROADCAST NEW AUCTION TO ALL CONNECTED BUYERS IN REAL-TIME
            try:
                from routes.socketio_events import broadcast_auction_created
                
                farmer = Farmer.query.get(farmer_id)
                auction_data = {
                    'auction_id': auction.id,
                    'crop_name': auction.crop_name,
                    'farmer_name': farmer.name if farmer else 'Unknown',
                    'quantity_quintals': auction.quantity_quintals,
                    'base_price_per_quintal': auction.base_price_per_quintal,
                    'quality_grade': auction.quality_grade,
                    'location': auction.location,
                    'district': auction.district,
                    'state': auction.state,
                    'minimum_bid_increment': auction.minimum_bid_increment,
                    'start_time': auction.start_time.isoformat(),
                    'end_time': auction.end_time.isoformat(),
                    'status': auction.status,
                    'description': auction.description,
                    'created_at': auction.created_at.isoformat()
                }
                
                broadcast_auction_created(auction_data)
                
            except Exception as e:
                print(f"❌ Error broadcasting auction: {str(e)}")
            
            return jsonify({
                'success': True,
                'auction_id': auction.id,
                'message': 'Auction created successfully'
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/auction/<auction_id>/edit', methods=['GET', 'POST'])
def edit_auction(auction_id):
    """Edit an existing auction"""
    if 'farmer_id_verified' not in session:
        return redirect(url_for('auth.login'))
    
    farmer_id = session['farmer_id_verified']
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return redirect(url_for('bidding.my_auctions'))
    
    # Check if this auction belongs to the current farmer
    if auction.farmer_id != farmer_id:
        return redirect(url_for('bidding.my_auctions'))
    
    # Only allow editing of active auctions with no bids
    if auction.status != 'active' or len(auction.bids) > 0:
        return render_template('farmer_auction_details.html', auction=auction, error='Cannot edit this auction')
    
    if request.method == 'GET':
        farmer = Farmer.query.get(farmer_id)
        return render_template('farmer_edit_auction.html', auction=auction, farmer=farmer)
    
    if request.method == 'POST':
        try:
            # Handle both FormData (with files) and JSON
            if request.is_json:
                data = request.get_json()
                photo_paths = {}
            else:
                data = request.form.to_dict()
                photo_paths = {}
                
                # Create uploads directory if it doesn't exist
                uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'auctions')
                os.makedirs(uploads_dir, exist_ok=True)
                
                # Handle photo uploads
                for i in range(1, 5):
                    file_key = f'photo{i}'
                    if file_key in request.files:
                        file = request.files[file_key]
                        if file and file.filename != '':
                            try:
                                filename = secure_filename(file.filename)
                                unique_filename = f"{uuid.uuid4()}_{filename}"
                                filepath = os.path.join(uploads_dir, unique_filename)
                                file.save(filepath)
                                # Store relative path for database
                                photo_paths[f'photo{i}_path'] = f'/static/uploads/auctions/{unique_filename}'
                            except Exception as e:
                                print(f"Error saving photo {i}: {str(e)}")
            
            # Validate required fields
            required_fields = ['crop_name', 'quantity_quintals', 'base_price_per_quintal', 'location', 'district']
            if not all(field in data for field in required_fields):
                return jsonify({'error': 'Missing required fields'}), 400
            
            # Update auction fields
            auction.crop_name = data['crop_name']
            auction.quantity_quintals = float(data['quantity_quintals'])
            auction.quality_grade = data.get('quality_grade', 'Standard')
            auction.base_price_per_quintal = float(data['base_price_per_quintal'])
            auction.minimum_bid_increment = float(data.get('minimum_bid_increment', 50))
            auction.location = data['location']
            auction.district = data['district']
            auction.state = data.get('state', 'Maharashtra')
            auction.description = data.get('description', '')
            auction.storage_location = data.get('storage_location', '')
            
            # Update harvest_date if provided
            if data.get('harvest_date'):
                try:
                    harvest_date_str = data['harvest_date']
                    if isinstance(harvest_date_str, str):
                        auction.harvest_date = datetime.strptime(harvest_date_str, '%Y-%m-%d').date()
                    else:
                        auction.harvest_date = harvest_date_str
                except:
                    pass
            
            # Update photos if new ones are provided
            for i in range(1, 5):
                if f'photo{i}_path' in photo_paths:
                    setattr(auction, f'photo{i}_path', photo_paths[f'photo{i}_path'])
            
            # Update current highest bid if base price changed
            if auction.current_highest_bid < float(data['base_price_per_quintal']):
                auction.current_highest_bid = float(data['base_price_per_quintal'])
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'auction_id': auction.id,
                'message': 'Auction updated successfully'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/my-auctions')
def my_auctions():
    """Get farmer's auctions"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    farmer_id = session['farmer_id_verified']
    auctions = Auction.query.filter_by(farmer_id=farmer_id).order_by(Auction.created_at.desc()).all()
    
    auctions_data = []
    for a in auctions:
        auction_dict = {
            'id': a.id,
            'crop_name': a.crop_name,
            'quantity_quintals': a.quantity_quintals,
            'base_price': a.base_price_per_quintal,
            'current_highest_bid': a.current_highest_bid,
            'status': a.status,
            'bids_count': len(a.bids),
            'start_time': a.start_time.isoformat(),
            'end_time': a.end_time.isoformat(),
            'created_at': a.created_at.isoformat()
        }
        
        # If auction is completed, find the winning buyer
        if a.status == 'completed' and a.bids:
            # Get the highest bid (winning bid)
            highest_bid = max(a.bids, key=lambda b: b.bid_price_per_quintal)
            if highest_bid.buyer:
                auction_dict['winning_buyer_name'] = highest_bid.buyer.buyer_name
                auction_dict['winning_company_name'] = highest_bid.buyer.company_name or 'N/A'
                auction_dict['winning_buyer_email'] = highest_bid.buyer.email
                auction_dict['winning_buyer_phone'] = highest_bid.buyer.phone or 'N/A'
                auction_dict['winning_buyer_address'] = highest_bid.buyer.address or 'N/A'
                auction_dict['winning_buyer_district'] = highest_bid.buyer.district or 'N/A'
                auction_dict['winning_buyer_state'] = highest_bid.buyer.state or 'N/A'
                auction_dict['winning_bid_price'] = highest_bid.bid_price_per_quintal
            else:
                auction_dict['winning_buyer_name'] = 'Unknown'
                auction_dict['winning_company_name'] = 'N/A'
                auction_dict['winning_buyer_email'] = 'N/A'
                auction_dict['winning_buyer_phone'] = 'N/A'
                auction_dict['winning_buyer_address'] = 'N/A'
                auction_dict['winning_buyer_district'] = 'N/A'
                auction_dict['winning_buyer_state'] = 'N/A'
                auction_dict['winning_bid_price'] = highest_bid.bid_price_per_quintal
        
        auctions_data.append(auction_dict)
    
    return jsonify({'auctions': auctions_data})


@bidding_bp.route('/farmer/auction/<auction_id>')
def auction_detail(auction_id):
    """Get auction details"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    
    if auction.farmer_id != session['farmer_id_verified']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'id': auction.id,
        'crop_name': auction.crop_name,
        'quantity_quintals': auction.quantity_quintals,
        'quality_grade': auction.quality_grade,
        'base_price': auction.base_price_per_quintal,
        'current_highest_bid': auction.current_highest_bid,
        'minimum_bid_increment': auction.minimum_bid_increment,
        'status': auction.status,
        'location': auction.location,
        'district': auction.district,
        'state': auction.state,
        'description': auction.description,
        'harvest_date': auction.harvest_date.isoformat() if auction.harvest_date else None,
        'storage_location': auction.storage_location,
        'start_time': auction.start_time.isoformat(),
        'end_time': auction.end_time.isoformat(),
        'bids_count': len(auction.bids),
        'created_at': auction.created_at.isoformat()
    })


@bidding_bp.route('/farmer/auction/<auction_id>/bids')
def auction_bids(auction_id):
    """View all bids for an auction"""
    if 'farmer_id_verified' not in session:
        return redirect(url_for('auth.login'))
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return redirect(url_for('bidding.farmer_dashboard'))
    
    if auction.farmer_id != session['farmer_id_verified']:
        return redirect(url_for('bidding.farmer_dashboard'))
    
    return render_template('farmer_auction_bids.html', auction=auction)


@bidding_bp.route('/farmer/auction/<auction_id>/details')
def auction_details_farmer(auction_id):
    """View auction details"""
    if 'farmer_id_verified' not in session:
        return redirect(url_for('auth.login'))
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return redirect(url_for('bidding.farmer_dashboard'))
    
    if auction.farmer_id != session['farmer_id_verified']:
        return redirect(url_for('bidding.farmer_dashboard'))
    
    # For completed auctions, fetch buyer details
    buyer_details = None
    if auction.status == 'completed' and auction.bids:
        highest_bid = max(auction.bids, key=lambda b: b.bid_price_per_quintal)
        if highest_bid.buyer:
            buyer_details = {
                'buyer_name': highest_bid.buyer.buyer_name,
                'company_name': highest_bid.buyer.company_name or 'N/A',
                'email': highest_bid.buyer.email,
                'phone': highest_bid.buyer.phone or 'N/A',
                'address': highest_bid.buyer.location or 'N/A',
                'district': highest_bid.buyer.district or 'N/A',
                'state': highest_bid.buyer.state or 'N/A',
                'winning_price': highest_bid.bid_price_per_quintal
            }
    
    return render_template('farmer_auction_details.html', auction=auction, buyer_details=buyer_details)


@bidding_bp.route('/farmer/auction/<auction_id>/api/bids')
def auction_bids_api(auction_id):
    """Get all bids for an auction (API endpoint)"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    
    if auction.farmer_id != session['farmer_id_verified']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    bids = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_price_per_quintal.desc()).all()
    
    return jsonify({
        'bids': [{
            'id': b.id,
            'bid_id': b.id,
            'buyer_id': b.buyer_id,
            'buyer_name': b.buyer.buyer_name if b.buyer else 'Unknown',
            'bid_price': b.bid_price_per_quintal,
            'bid_total': b.bid_total_amount,
            'status': b.status,
            'created_at': b.created_at.isoformat()
        } for b in bids]
    })


@bidding_bp.route('/farmer/auction/<auction_id>/api')
def farmer_auction_api(auction_id):
    """Get auction details with bids (for counter offer selection)"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    
    if auction.farmer_id != session['farmer_id_verified']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    bids = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_price_per_quintal.desc()).all()
    
    return jsonify({
        'auction': {
            'id': auction.id,
            'crop_name': auction.crop_name,
            'bids': [{
                'bid_id': b.id,
                'buyer_id': b.buyer_id,
                'buyer_name': b.buyer.buyer_name if b.buyer else 'Unknown',
                'company_name': b.buyer.company_name if b.buyer else 'Unknown',
                'bid_price': b.bid_price_per_quintal,
                'bid_total': b.bid_total_amount,
                'status': b.status,
                'created_at': b.created_at.isoformat()
            } for b in bids]
        }
    })


@bidding_bp.route('/buyer/auction/<auction_id>/all-bids', methods=['GET'])
def get_all_auction_bids(auction_id):
    """Get all bids placed on an auction (for buyer to see competition)"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        auction = Auction.query.get(auction_id)
        
        if not auction:
            return jsonify({'error': 'Auction not found'}), 404
        
        # Get all bids sorted by price descending
        bids = Bid.query.filter_by(auction_id=auction_id).order_by(
            Bid.bid_price_per_quintal.desc()
        ).all()
        
        bids_data = []
        for idx, bid in enumerate(bids, 1):
            buyer = Buyer.query.get(bid.buyer_id)
            bids_data.append({
                'rank': idx,
                'bid_id': bid.id,
                'buyer_id': bid.buyer_id,
                'buyer_name': buyer.buyer_name if buyer else 'Unknown',
                'company_name': buyer.company_name if buyer else 'Unknown',
                'bid_price': bid.bid_price_per_quintal,
                'bid_total': bid.bid_total_amount,
                'status': bid.status,
                'created_at': bid.created_at.isoformat(),
                'is_my_bid': bid.buyer_id == session['buyer_id_verified']
            })
        
        return jsonify({
            'success': True,
            'auction_id': auction_id,
            'crop_name': auction.crop_name,
            'quantity': auction.quantity_quintals,
            'total_bids': len(bids_data),
            'bids': bids_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/auction/<auction_id>/api/counter-offers', methods=['GET'])
def get_counter_offers(auction_id):
    """Get all counter offers sent for this auction"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    
    if auction.farmer_id != session['farmer_id_verified']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    counter_offers = CounterOffer.query.filter_by(auction_id=auction_id).order_by(CounterOffer.created_at.desc()).all()
    
    offers_list = []
    for co in counter_offers:
        # Get bid to fetch original bid price and buyer info
        bid = Bid.query.get(co.bid_id)
        company_name = 'Unknown'
        original_bid = 0
        
        if bid:
            original_bid = bid.bid_price_per_quintal
            if bid.buyer:
                company_name = bid.buyer.company_name or bid.buyer.buyer_name
        
        offers_list.append({
            'id': co.id,
            'bid_id': co.bid_id,
            'buyer_id': co.buyer_id,
            'company_name': company_name,
            'original_bid': original_bid,
            'counter_price': co.counter_price_per_quintal,
            'status': co.status,
            'created_at': co.created_at.isoformat()
        })
    
    return jsonify({'counter_offers': offers_list})


@bidding_bp.route('/farmer/auction/<auction_id>/accept-bid', methods=['POST'])
def accept_bid(auction_id):
    """Accept a bid and close the auction"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    
    if auction.farmer_id != session['farmer_id_verified']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        bid_id = data.get('bid_id')
        
        bid = Bid.query.get(bid_id)
        
        if not bid or bid.auction_id != auction_id:
            return jsonify({'error': 'Bid not found'}), 404
        
        # Update bid status
        bid.status = 'accepted'
        
        # Update auction status
        auction.status = 'completed'
        auction.current_highest_bid = bid.bid_price_per_quintal
        
        # Mark other bids as rejected
        for other_bid in auction.bids:
            if other_bid.id != bid_id:
                other_bid.status = 'rejected'
        
        # Create notifications
        notification = AuctionNotification(
            id=str(uuid.uuid4()),
            user_id=bid.buyer_id,
            user_type='buyer',
            auction_id=auction_id,
            notification_type='bid_accepted',
            message=f'Your bid of ₹{bid.bid_price_per_quintal}/quintal has been accepted!'
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # 📢 BROADCAST BID ACCEPTANCE TO ALL CONNECTED BUYERS IN REAL-TIME
        try:
            from routes.socketio_events import broadcast_bid_accepted
            
            bid_data = {
                'auction_id': auction_id,
                'bid_id': bid_id,
                'winning_buyer_id': bid.buyer_id,
                'winning_price': bid.bid_price_per_quintal,
                'crop_name': auction.crop_name,
                'farmer_name': auction.farmer.name if auction.farmer else 'Unknown',
                'quantity': auction.quantity_quintals
            }
            broadcast_bid_accepted(bid_data)
        except Exception as e:
            print(f"❌ Error broadcasting bid acceptance: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Bid accepted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/auction/<auction_id>/reject-bid', methods=['POST'])
def reject_bid(auction_id):
    """Reject a bid"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    
    if auction.farmer_id != session['farmer_id_verified']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        bid_id = data.get('bid_id')
        
        bid = Bid.query.get(bid_id)
        
        if not bid or bid.auction_id != auction_id:
            return jsonify({'error': 'Bid not found'}), 404
        
        bid.status = 'rejected'
        
        # Create notification for buyer
        notification = AuctionNotification(
            id=str(uuid.uuid4()),
            user_id=bid.buyer_id,
            user_type='buyer',
            auction_id=auction_id,
            notification_type='bid_rejected',
            message=f'Your bid of ₹{bid.bid_price_per_quintal}/quintal has been rejected.'
        )
        
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Bid rejected'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/auction/<auction_id>/counter-offer', methods=['POST'])
def send_counter_offer(auction_id):
    """Send a counter offer to a bid"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    
    if auction.farmer_id != session['farmer_id_verified']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        bid_id = data.get('bid_id')
        counter_price = data.get('counter_price')
        
        # Validate inputs
        if not bid_id or counter_price is None:
            return jsonify({'error': 'Missing required fields: bid_id and counter_price'}), 400
        
        try:
            counter_price = float(counter_price)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid counter price. Must be a number.'}), 400
        
        if counter_price <= 0:
            return jsonify({'error': 'Counter price must be positive'}), 400
        
        bid = Bid.query.get(bid_id)
        
        if not bid or bid.auction_id != auction_id:
            return jsonify({'error': 'Bid not found'}), 404
        
        # Create counter offer
        counter_offer = CounterOffer(
            id=str(uuid.uuid4()),
            auction_id=auction_id,
            bid_id=bid_id,
            buyer_id=bid.buyer_id,
            counter_price_per_quintal=counter_price,
            status='pending'
        )
        
        # Create notification for buyer
        notification = AuctionNotification(
            id=str(uuid.uuid4()),
            user_id=bid.buyer_id,
            user_type='buyer',
            auction_id=auction_id,
            notification_type='counter_offer',
            message=f'Farmer sent a counter offer: ₹{counter_price}/quintal'
        )
        
        db.session.add(counter_offer)
        db.session.add(notification)
        db.session.commit()
        
        # 📢 BROADCAST COUNTER OFFER TO BUYER IN REAL-TIME
        try:
            from routes.socketio_events import broadcast_counter_offer_sent
            
            co_data = {
                'auction_id': auction_id,
                'counter_offer_id': counter_offer.id,
                'bid_id': bid_id,
                'buyer_id': bid.buyer_id,
                'counter_price': counter_price,
                'farmer_name': auction.farmer.name if auction.farmer else 'Unknown',
                'crop_name': auction.crop_name,
                'quantity': auction.quantity_quintals
            }
            broadcast_counter_offer_sent(co_data)
        except Exception as e:
            print(f"❌ Error broadcasting counter offer: {str(e)}")
        
        return jsonify({
            'success': True,
            'counter_offer_id': counter_offer.id,
            'message': 'Counter offer sent'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/auction/<auction_id>/extend', methods=['POST'])
def extend_auction(auction_id):
    """Extend auction duration"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    
    if auction.farmer_id != session['farmer_id_verified']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        additional_hours = int(data.get('additional_hours', 1))
        
        auction.end_time = auction.end_time + timedelta(hours=additional_hours)
        
        # Create notifications
        for bid in auction.bids:
            notification = AuctionNotification(
                id=str(uuid.uuid4()),
                user_id=bid.buyer_id,
                user_type='buyer',
                auction_id=auction_id,
                notification_type='auction_extended',
                message=f'Auction extended by {additional_hours} hour(s)'
            )
            db.session.add(notification)
        
        db.session.commit()
        
        # 📢 BROADCAST AUCTION EXTENSION TO ALL BUYERS IN REAL-TIME
        try:
            from routes.socketio_events import broadcast_auction_extended
            
            extend_data = {
                'auction_id': auction_id,
                'new_end_time': auction.end_time.isoformat(),
                'additional_hours': additional_hours,
                'crop_name': auction.crop_name,
                'farmer_name': auction.farmer.name if auction.farmer else 'Unknown'
            }
            broadcast_auction_extended(extend_data)
        except Exception as e:
            print(f"❌ Error broadcasting auction extension: {str(e)}")
        
        return jsonify({
            'success': True,
            'new_end_time': auction.end_time.isoformat(),
            'message': f'Auction extended by {additional_hours} hour(s)'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/auction/<auction_id>/update-price', methods=['POST'])
def update_minimum_price(auction_id):
    """Update minimum bid price for auction"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    
    if auction.farmer_id != session['farmer_id_verified']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Accept both 'new_minimum_price' and 'minimum_price' keys
        new_minimum = data.get('new_minimum_price') or data.get('minimum_price')
        
        if not new_minimum:
            return jsonify({'error': 'Minimum price is required'}), 400
        
        new_minimum = float(new_minimum)
        
        if new_minimum <= 0:
            return jsonify({'error': 'Minimum price must be positive'}), 400
        
        auction.base_price_per_quintal = new_minimum
        db.session.commit()
        
        # 📢 BROADCAST AUCTION PRICE UPDATE TO ALL BUYERS IN REAL-TIME
        try:
            from routes.socketio_events import broadcast_auction_price_updated
            
            price_data = {
                'auction_id': auction_id,
                'new_minimum_price': new_minimum,
                'crop_name': auction.crop_name,
                'farmer_name': auction.farmer.name if auction.farmer else 'Unknown'
            }
            broadcast_auction_price_updated(price_data)
        except Exception as e:
            print(f"❌ Error broadcasting price update: {str(e)}")
        
        return jsonify({
            'success': True,
            'new_minimum': new_minimum,
            'message': 'Minimum price updated successfully'
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Invalid price format. Please enter a valid number'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/auction/<auction_id>/cancel', methods=['POST'])
def cancel_auction(auction_id):
    """Cancel an auction"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    auction = Auction.query.get(auction_id)
    
    if not auction:
        return jsonify({'error': 'Auction not found'}), 404
    
    if auction.farmer_id != session['farmer_id_verified']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        auction.status = 'cancelled'
        
        # Notify all bidders
        for bid in auction.bids:
            notification = AuctionNotification(
                id=str(uuid.uuid4()),
                user_id=bid.buyer_id,
                user_type='buyer',
                auction_id=auction_id,
                notification_type='auction_cancelled',
                message='The auction has been cancelled by the farmer'
            )
            db.session.add(notification)
        
        db.session.commit()
        
        # 📢 BROADCAST AUCTION CANCELLATION TO ALL BUYERS IN REAL-TIME
        try:
            from routes.socketio_events import broadcast_auction_cancelled
            
            cancel_data = {
                'auction_id': auction_id,
                'crop_name': auction.crop_name,
                'farmer_name': auction.farmer.name if auction.farmer else 'Unknown'
            }
            broadcast_auction_cancelled(cancel_data)
        except Exception as e:
            print(f"❌ Error broadcasting auction cancellation: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Auction cancelled'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/dashboard/stats')
def farmer_stats():
    """Get farmer's bidding dashboard statistics"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    farmer_id = session['farmer_id_verified']
    
    # Count auctions by status
    total_auctions = Auction.query.filter_by(farmer_id=farmer_id).count()
    active_auctions = Auction.query.filter_by(farmer_id=farmer_id, status='active').count()
    completed_auctions = Auction.query.filter_by(farmer_id=farmer_id, status='completed').count()
    cancelled_auctions = Auction.query.filter_by(farmer_id=farmer_id, status='cancelled').count()
    
    # Get best prices
    all_auctions = Auction.query.filter_by(farmer_id=farmer_id).all()
    best_price = max([a.current_highest_bid for a in all_auctions], default=0)
    
    # Total bids received
    total_bids = sum([len(a.bids) for a in all_auctions])
    
    return jsonify({
        'total_auctions': total_auctions,
        'active_auctions': active_auctions,
        'completed_auctions': completed_auctions,
        'cancelled_auctions': cancelled_auctions,
        'best_price': best_price,
        'total_bids': total_bids
    })


# ==================== BUYER-SIDE ENDPOINTS ====================

@bidding_bp.route('/buyer/dashboard')
def buyer_dashboard():
    """Buyer's main dashboard with auctions, chats, and profile"""
    if 'buyer_id_verified' not in session:
        return redirect(url_for('buyer_auth.buyer_login'))
    
    buyer_id = session['buyer_id_verified']
    buyer = Buyer.query.get(buyer_id)
    
    if not buyer:
        return redirect(url_for('buyer_auth.buyer_login'))
    
    return render_template('buyer_dashboard.html', buyer=buyer)


@bidding_bp.route('/buyer/browse-auctions')
def browse_auctions():
    """Browse all active auctions - redirect to dashboard"""
    if 'buyer_id_verified' not in session:
        return redirect(url_for('buyer_auth.buyer_login'))
    
    buyer_id = session['buyer_id_verified']
    buyer = Buyer.query.get(buyer_id)
    return render_template('buyer_dashboard.html', buyer=buyer)


@bidding_bp.route('/buyer/auctions/api', methods=['GET'])
def get_auctions():
    """Get list of active auctions with filters"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        buyer_id = session['buyer_id_verified']
        
        # Get filter parameters
        crop_filter = request.args.get('crop', '').strip()
        district_filter = request.args.get('district', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 12
        
        # Build query - exclude auctions where buyer has already bid
        query = Auction.query.filter_by(status='active')
        
        # Get auction IDs where this buyer has already placed a bid
        buyer_bid_auction_ids = db.session.query(Bid.auction_id).filter_by(buyer_id=buyer_id).all()
        buyer_bid_auction_ids = [bid[0] for bid in buyer_bid_auction_ids]
        
        # Exclude those auctions
        if buyer_bid_auction_ids:
            query = query.filter(~Auction.id.in_(buyer_bid_auction_ids))
        
        if crop_filter:
            query = query.filter(Auction.crop_name.ilike(f'%{crop_filter}%'))
        
        if district_filter:
            query = query.filter(Auction.district.ilike(f'%{district_filter}%'))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        auctions = query.order_by(Auction.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        result = {
            'total': total,
            'page': page,
            'pages': auctions.pages,
            'auctions': []
        }
        
        for auction in auctions.items:
            farmer = Farmer.query.get(auction.farmer_id)
            bids_count = len(auction.bids)
            highest_bid = auction.current_highest_bid
            
            # Calculate time remaining
            now = datetime.utcnow()
            time_remaining = (auction.end_time - now).total_seconds()
            
            result['auctions'].append({
                'id': auction.id,
                'crop_name': auction.crop_name,
                'quantity_quintals': auction.quantity_quintals,
                'base_price': auction.base_price_per_quintal,
                'highest_bid': highest_bid,
                'quality_grade': auction.quality_grade,
                'location': auction.location,
                'district': auction.district,
                'farmer_name': farmer.name if farmer else 'Unknown',
                'bids_count': bids_count,
                'status': auction.status,
                'time_remaining': max(0, time_remaining),
                'created_at': auction.created_at.isoformat()
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/auction/<auction_id>')
def auction_details(auction_id):
    """View detailed auction information - loads via dashboard"""
    if 'buyer_id_verified' not in session:
        return redirect(url_for('buyer_auth.buyer_login'))
    
    buyer_id = session['buyer_id_verified']
    buyer = Buyer.query.get(buyer_id)
    return render_template('buyer_dashboard.html', buyer=buyer, auction_id=auction_id)


@bidding_bp.route('/buyer/auction/<auction_id>/api', methods=['GET'])
def get_auction_details(auction_id):
    """Get detailed auction information"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        auction = Auction.query.get(auction_id)
        
        if not auction:
            return jsonify({'error': 'Auction not found'}), 404
        
        farmer = Farmer.query.get(auction.farmer_id)
        buyer_id = session['buyer_id_verified']
        
        # Get buyer's bid if exists
        my_bid = Bid.query.filter_by(auction_id=auction_id, buyer_id=buyer_id).first()
        
        # Get all bids for this auction
        all_bids = Bid.query.filter_by(auction_id=auction_id).order_by(
            Bid.bid_price_per_quintal.desc()
        ).all()
        
        now = datetime.utcnow()
        time_remaining = max(0, (auction.end_time - now).total_seconds())
        
        result = {
            'id': auction.id,
            'crop_name': auction.crop_name,
            'quantity_quintals': auction.quantity_quintals,
            'quality_grade': auction.quality_grade,
            'base_price': auction.base_price_per_quintal,
            'current_highest_bid': auction.current_highest_bid,
            'minimum_bid_increment': auction.minimum_bid_increment,
            'location': auction.location,
            'district': auction.district,
            'state': auction.state,
            'description': auction.description or '',
            'harvest_date': auction.harvest_date.isoformat() if auction.harvest_date else None,
            'storage_location': auction.storage_location or '',
            'photo1_path': auction.photo1_path,
            'photo2_path': auction.photo2_path,
            'photo3_path': auction.photo3_path,
            'photo4_path': auction.photo4_path,
            'start_time': auction.start_time.isoformat(),
            'end_time': auction.end_time.isoformat(),
            'time_remaining': time_remaining,
            'status': auction.status,
            'farmer_name': farmer.name if farmer else 'Unknown',
            'farmer_location': farmer.district if farmer else 'Unknown',
            'bids_count': len(all_bids),
            'my_bid': {
                'bid_id': my_bid.id,
                'bid_price': my_bid.bid_price_per_quintal,
                'bid_total': my_bid.bid_total_amount,
                'status': my_bid.status,
                'created_at': my_bid.created_at.isoformat()
            } if my_bid else None,
            'top_bids': [
                {
                    'buyer_id': bid.buyer_id,
                    'bid_price': bid.bid_price_per_quintal,
                    'bid_total': bid.bid_total_amount,
                    'created_at': bid.created_at.isoformat()
                }
                for bid in all_bids[:5]
            ]
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/auction/<auction_id>/place-bid', methods=['POST'])
def place_bid(auction_id):
    """Place a bid on an auction"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        auction = Auction.query.get(auction_id)
        
        if not auction:
            return jsonify({'error': 'Auction not found'}), 404
        
        if auction.status != 'active':
            return jsonify({'error': 'This auction is no longer active'}), 400
        
        # Check if auction has ended
        if datetime.utcnow() > auction.end_time:
            auction.status = 'closed'
            db.session.commit()
            return jsonify({'error': 'Auction has ended'}), 400
        
        data = request.get_json()
        bid_price = float(data.get('bid_price', 0))
        
        if bid_price <= 0:
            return jsonify({'error': 'Bid price must be positive'}), 400
        
        # Check if bid meets minimum requirements
        if bid_price < auction.base_price_per_quintal:
            return jsonify({'error': f'Bid must be at least ₹{auction.base_price_per_quintal}/q'}), 400
        
        if bid_price < auction.current_highest_bid:
            return jsonify({'error': f'Bid must be at least ₹{auction.current_highest_bid}/q'}), 400
        
        # Check minimum increment
        if bid_price < auction.current_highest_bid + auction.minimum_bid_increment:
            return jsonify({
                'error': f'Bid must increase by at least ₹{auction.minimum_bid_increment}/q'
            }), 400
        
        # Check if buyer already has a bid
        existing_bid = Bid.query.filter_by(auction_id=auction_id, buyer_id=buyer_id).first()
        
        if existing_bid:
            # Update existing bid
            existing_bid.bid_price_per_quintal = bid_price
            existing_bid.bid_total_amount = bid_price * auction.quantity_quintals
            existing_bid.updated_at = datetime.utcnow()
        else:
            # Create new bid
            bid = Bid(
                id=str(uuid.uuid4()),
                auction_id=auction_id,
                buyer_id=buyer_id,
                bid_price_per_quintal=bid_price,
                bid_total_amount=bid_price * auction.quantity_quintals,
                status='active'
            )
            db.session.add(bid)
        
        # Update auction's highest bid
        auction.current_highest_bid = bid_price
        auction.updated_at = datetime.utcnow()
        
        # Create notification for farmer
        notification = AuctionNotification(
            id=str(uuid.uuid4()),
            user_id=auction.farmer_id,
            user_type='farmer',
            auction_id=auction_id,
            notification_type='new_bid',
            message=f'New bid received: ₹{bid_price}/q'
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # 📢 BROADCAST BID UPDATE TO ALL CONNECTED BUYERS AND FARMER IN REAL-TIME
        try:
            from routes.socketio_events import broadcast_bid_placed
            
            # Calculate minimum bid required for next bid
            minimum_bid_increment = auction.minimum_bid_increment
            next_minimum_bid = bid_price + minimum_bid_increment
            
            bid_data = {
                'auction_id': auction_id,
                'bid_price_per_quintal': bid_price,
                'bid_total_amount': bid_price * auction.quantity_quintals,
                'buyer_count': len(auction.bids),
                'highest_bid': auction.current_highest_bid,
                'minimum_bid_increment': minimum_bid_increment,
                'minimum_bid_required': next_minimum_bid
            }
            broadcast_bid_placed(auction_id, bid_data)
        except Exception as e:
            print(f"❌ Error broadcasting bid: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Bid placed successfully',
            'bid_id': existing_bid.id if existing_bid else bid.id,
            'bid_price': bid_price,
            'bid_total': bid_price * auction.quantity_quintals
        }), 201
        
    except ValueError as e:
        return jsonify({'error': 'Invalid bid price format'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/counter-offers/api', methods=['GET'])
def get_buyer_counter_offers():
    """Get counter offers received by buyer"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        # Get all counter offers for this buyer
        counter_offers = CounterOffer.query.filter_by(buyer_id=buyer_id).all()
        
        offers_data = []
        for co in counter_offers:
            bid = Bid.query.get(co.bid_id)
            auction = Auction.query.get(co.auction_id)
            
            if auction and bid:
                offers_data.append({
                    'id': co.id,
                    'counter_offer_id': co.id,
                    'auction_id': co.auction_id,
                    'bid_id': co.bid_id,
                    'crop_name': auction.crop_name,
                    'quantity_quintals': auction.quantity_quintals,
                    'your_bid': bid.bid_price_per_quintal,
                    'counter_price': co.counter_price_per_quintal,
                    'status': co.status,
                    'created_at': co.created_at.isoformat(),
                    'farmer_name': auction.farmer.name if auction.farmer else 'Unknown',
                    'location': auction.location,
                    'district': auction.district
                })
        
        return jsonify({
            'counter_offers': offers_data,
            'total': len(offers_data)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/counter-offer/<counter_offer_id>/accept', methods=['POST'])
def accept_counter_offer(counter_offer_id):
    """Accept a counter offer from farmer"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        counter_offer = CounterOffer.query.get(counter_offer_id)
        
        if not counter_offer:
            return jsonify({'error': 'Counter offer not found'}), 404
        
        if counter_offer.buyer_id != buyer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update counter offer status
        counter_offer.status = 'accepted'
        counter_offer.updated_at = datetime.utcnow()
        
        # Update bid with counter price
        bid = Bid.query.get(counter_offer.bid_id)
        if bid:
            bid.bid_price_per_quintal = counter_offer.counter_price_per_quintal
            bid.bid_total_amount = counter_offer.counter_price_per_quintal * bid.auction.quantity_quintals
            bid.updated_at = datetime.utcnow()
        
        # Update auction
        auction = Auction.query.get(counter_offer.auction_id)
        if auction:
            auction.current_highest_bid = counter_offer.counter_price_per_quintal
            auction.updated_at = datetime.utcnow()
        
        # Create notification for farmer
        notification = AuctionNotification(
            id=str(uuid.uuid4()),
            user_id=auction.farmer_id,
            user_type='farmer',
            auction_id=counter_offer.auction_id,
            notification_type='counter_offer_accepted',
            message=f'Buyer accepted counter offer: ₹{counter_offer.counter_price_per_quintal}/quintal'
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # 📢 BROADCAST COUNTER OFFER ACCEPTANCE TO FARMER IN REAL-TIME
        try:
            from routes.socketio_events import broadcast_counter_offer_response
            
            response_data = {
                'auction_id': counter_offer.auction_id,
                'counter_offer_id': counter_offer.id,
                'bid_id': counter_offer.bid_id,
                'buyer_id': counter_offer.buyer_id,
                'status': 'accepted',
                'counter_price': counter_offer.counter_price_per_quintal,
                'crop_name': auction.crop_name if auction else 'Unknown'
            }
            broadcast_counter_offer_response(response_data)
        except Exception as e:
            print(f"❌ Error broadcasting counter offer acceptance: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Counter offer accepted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/counter-offer/<counter_offer_id>/reject', methods=['POST'])
def reject_counter_offer(counter_offer_id):
    """Reject a counter offer from farmer"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        counter_offer = CounterOffer.query.get(counter_offer_id)
        
        if not counter_offer:
            return jsonify({'error': 'Counter offer not found'}), 404
        
        if counter_offer.buyer_id != buyer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update counter offer status
        counter_offer.status = 'rejected'
        counter_offer.updated_at = datetime.utcnow()
        
        # Create notification for farmer
        auction = Auction.query.get(counter_offer.auction_id)
        if auction:
            notification = AuctionNotification(
                id=str(uuid.uuid4()),
                user_id=auction.farmer_id,
                user_type='farmer',
                auction_id=counter_offer.auction_id,
                notification_type='counter_offer_rejected',
                message='Buyer rejected your counter offer'
            )
            db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Counter offer rejected'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/my-bids')
def my_bids():
    """View buyer's bids - redirect to dashboard"""
    if 'buyer_id_verified' not in session:
        return redirect(url_for('buyer_auth.buyer_login'))
    
    buyer_id = session['buyer_id_verified']
    buyer = Buyer.query.get(buyer_id)
    return render_template('buyer_dashboard.html', buyer=buyer)


@bidding_bp.route('/buyer/bids/api', methods=['GET'])
def get_my_bids():
    """Get buyer's all bids"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        # Get all bids by this buyer
        bids = Bid.query.filter_by(buyer_id=buyer_id).order_by(
            Bid.created_at.desc()
        ).all()
        
        result = {
            'total_bids': len(bids),
            'bids': []
        }
        
        for bid in bids:
            auction = Auction.query.get(bid.auction_id)
            farmer = Farmer.query.get(auction.farmer_id)
            
            now = datetime.utcnow()
            auction_active = auction.status == 'active' and now < auction.end_time
            is_winning = bid.bid_price_per_quintal == auction.current_highest_bid
            
            # Determine bid status
            # Status logic:
            # - 'pending' if auction is still active and bid hasn't been accepted
            # - 'won' if bid was accepted by farmer (auction completed)
            # - 'cancelled' if auction was cancelled by farmer
            # - 'ended' if auction ended but this bid was not accepted (auction closed)
            
            if auction.status == 'cancelled':
                bid_status = 'cancelled'
            elif auction.status == 'completed':
                bid_status = 'won' if is_winning else 'ended'
            elif auction.status == 'active' and now >= auction.end_time:
                bid_status = 'ended'
            elif auction.status == 'closed':
                bid_status = 'ended'
            else:
                bid_status = 'pending'
            
            result['bids'].append({
                'bid_id': bid.id,
                'auction_id': bid.auction_id,
                'crop_name': auction.crop_name,
                'bid_price': bid.bid_price_per_quintal,
                'bid_total': bid.bid_total_amount,
                'quantity': auction.quantity_quintals,
                'highest_bid': auction.current_highest_bid,
                'base_price': auction.base_price_per_quintal,
                'minimum_bid_increment': auction.minimum_bid_increment or 0,
                'status': bid_status,
                'auction_status': auction.status,
                'is_winning': is_winning,
                'auction_active': auction_active,
                'farmer_name': farmer.name if farmer else 'Unknown',
                'farmer_phone': farmer.phone_number if farmer else None,
                'location': auction.location,
                'bid_date': bid.created_at.isoformat(),
                'auction_end': auction.end_time.isoformat()
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/won-auctions')
def won_auctions():
    """View buyer's won auctions - redirect to dashboard"""
    if 'buyer_id_verified' not in session:
        return redirect(url_for('buyer_auth.buyer_login'))
    
    buyer_id = session['buyer_id_verified']
    buyer = Buyer.query.get(buyer_id)
    return render_template('buyer_dashboard.html', buyer=buyer)


@bidding_bp.route('/buyer/won-auctions/api', methods=['GET'])
def get_won_auctions():
    """Get buyer's completed/won auctions"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        # Get all auctions where this buyer has the winning bid
        won_auctions = []
        
        buyer_bids = Bid.query.filter_by(buyer_id=buyer_id).all()
        
        for bid in buyer_bids:
            auction = Auction.query.get(bid.auction_id)
            
            # Check if this bid is the highest and auction is completed
            if (bid.bid_price_per_quintal == auction.current_highest_bid and 
                auction.status == 'completed'):
                
                farmer = Farmer.query.get(auction.farmer_id)
                
                won_auctions.append({
                    'auction_id': auction.id,
                    'crop_name': auction.crop_name,
                    'quantity': auction.quantity_quintals,
                    'winning_price': bid.bid_price_per_quintal,
                    'total_amount': bid.bid_total_amount,
                    'location': auction.location,
                    'farmer_name': farmer.name if farmer else 'Unknown',
                    'auction_date': auction.created_at.isoformat(),
                    'completed_date': auction.updated_at.isoformat()
                })
        
        result = {
            'total_won': len(won_auctions),
            'auctions': won_auctions
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/notifications')
def buyer_notifications():
    """View buyer's notifications"""
    if 'buyer_id_verified' not in session:
        return redirect(url_for('buyer_auth.buyer_login'))
    
    return render_template('buyer_notifications.html')


@bidding_bp.route('/buyer/notifications/api', methods=['GET'])
def get_buyer_notifications():
    """Get buyer's notifications"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        # Get all notifications for buyer
        notifications = AuctionNotification.query.filter_by(
            user_id=buyer_id,
            user_type='buyer'
        ).order_by(AuctionNotification.created_at.desc()).all()
        
        result = {
            'unread_count': sum(1 for n in notifications if not n.is_read),
            'total_count': len(notifications),
            'notifications': []
        }
        
        for notif in notifications:
            auction = Auction.query.get(notif.auction_id)
            
            result['notifications'].append({
                'notification_id': notif.id,
                'type': notif.notification_type,
                'message': notif.message,
                'auction_id': notif.auction_id,
                'crop_name': auction.crop_name if auction else 'Unknown',
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat()
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/notifications/<notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """Mark notification as read"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        notification = AuctionNotification.query.get(notification_id)
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        if notification.user_id != session['buyer_id_verified']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/dashboard/stats')
def buyer_stats():
    """Get buyer's dashboard statistics"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        # Count bids
        total_bids = Bid.query.filter_by(buyer_id=buyer_id).count()
        
        # Count active bids (auctions still open)
        active_bids = 0
        for bid in Bid.query.filter_by(buyer_id=buyer_id).all():
            auction = Auction.query.get(bid.auction_id)
            if auction.status == 'active' and datetime.utcnow() < auction.end_time:
                active_bids += 1
        
        # Count winning bids
        winning_bids = 0
        for bid in Bid.query.filter_by(buyer_id=buyer_id).all():
            auction = Auction.query.get(bid.auction_id)
            if bid.bid_price_per_quintal == auction.current_highest_bid and auction.status != 'cancelled':
                winning_bids += 1
        
        # Count won auctions (completed)
        won_auctions = 0
        for bid in Bid.query.filter_by(buyer_id=buyer_id).all():
            auction = Auction.query.get(bid.auction_id)
            if bid.bid_price_per_quintal == auction.current_highest_bid and auction.status == 'completed':
                won_auctions += 1
        
        # Get unread notifications
        unread_notifications = AuctionNotification.query.filter_by(
            user_id=buyer_id,
            user_type='buyer',
            is_read=False
        ).count()
        
        return jsonify({
            'total_bids': total_bids,
            'active_bids': active_bids,
            'winning_bids': winning_bids,
            'won_auctions': won_auctions,
            'unread_notifications': unread_notifications
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== AUCTION CHAT SYSTEM ====================

@bidding_bp.route('/buyer/chat/initiate', methods=['POST'])
def initiate_chat():
    """Buyer initiates chat with farmer when winning auction"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        data = request.get_json()
        auction_id = data.get('auction_id')
        initial_message = data.get('message', '')
        
        if not auction_id:
            return jsonify({'error': 'Auction ID required'}), 400
        
        auction = Auction.query.get(auction_id)
        if not auction:
            return jsonify({'error': 'Auction not found'}), 404
        
        farmer_id = auction.farmer_id
        
        # Check if chat already exists for this buyer-farmer pair on this auction
        from models_marketplace_keep import Chat, ChatMessage
        existing_chat = Chat.query.filter_by(
            buyer_id=buyer_id,
            farmer_id=farmer_id,
            auction_id=auction_id
        ).first()
        
        if existing_chat:
            chat = existing_chat
        else:
            # Create new chat
            chat = Chat(
                buyer_id=buyer_id,
                farmer_id=farmer_id,
                auction_id=auction_id,
                crop_name=auction.crop_name
            )
            db.session.add(chat)
            db.session.flush()
        
        # Add initial message if provided
        if initial_message.strip():
            buyer = Buyer.query.get(buyer_id)
            message = ChatMessage(
                chat_id=chat.id,
                sender_type='buyer',
                sender_id=buyer_id,
                sender_name=buyer.buyer_name if buyer else 'Buyer',
                message=initial_message,
                is_read=False
            )
            db.session.add(message)
            chat.last_message_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'chat_id': chat.id,
            'message': 'Chat initiated successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/chats/list', methods=['GET'])
def get_buyer_chats():
    """Get all chats for buyer"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        from models_marketplace_keep import Chat
        chats = Chat.query.filter_by(buyer_id=buyer_id, is_active=True).order_by(
            Chat.last_message_at.desc()
        ).all()
        
        chats_data = []
        for chat in chats:
            farmer = Farmer.query.get(chat.farmer_id)
            unread_count = sum(1 for msg in chat.messages if not msg.is_read and msg.sender_type == 'farmer')
            last_message = chat.messages[-1] if chat.messages else None
            
            chats_data.append({
                'chat_id': chat.id,
                'auction_id': chat.auction_id,
                'farmer_id': chat.farmer_id,
                'farmer_name': farmer.name if farmer else 'Unknown Farmer',
                'crop_name': chat.crop_name,
                'unread_count': unread_count,
                'last_message': last_message.message if last_message else 'No messages yet',
                'last_message_time': last_message.created_at.isoformat() if last_message else None,
                'last_message_sender': last_message.sender_type if last_message else None,
                'updated_at': chat.updated_at.isoformat()
            })
        
        return jsonify({
            'chats': chats_data,
            'total': len(chats_data)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/chat/<chat_id>/messages', methods=['GET'])
def get_chat_messages(chat_id):
    """Get messages in a chat"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        from models_marketplace_keep import Chat
        chat = Chat.query.get(chat_id)
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        if chat.buyer_id != buyer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Mark farmer messages as read
        for message in chat.messages:
            if message.sender_type == 'farmer' and not message.is_read:
                message.is_read = True
        db.session.commit()
        
        messages_data = [{
            'message_id': msg.id,
            'sender_type': msg.sender_type,
            'sender_name': msg.sender_name,
            'message': msg.message,
            'timestamp': msg.created_at.isoformat(),
            'is_read': msg.is_read
        } for msg in chat.messages]
        
        return jsonify({
            'chat_id': chat_id,
            'messages': messages_data,
            'total': len(messages_data)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/buyer/chat/<chat_id>/send', methods=['POST'])
def send_buyer_message(chat_id):
    """Send a message in chat (buyer)"""
    if 'buyer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    buyer_id = session['buyer_id_verified']
    
    try:
        from models_marketplace_keep import Chat, ChatMessage
        chat = Chat.query.get(chat_id)
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        if chat.buyer_id != buyer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        buyer = Buyer.query.get(buyer_id)
        message = ChatMessage(
            chat_id=chat_id,
            sender_type='buyer',
            sender_id=buyer_id,
            sender_name=buyer.buyer_name if buyer else 'Buyer',
            message=message_text,
            is_read=False
        )
        
        chat.last_message_at = datetime.utcnow()
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_id': message.id,
            'timestamp': message.created_at.isoformat()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/chats/list', methods=['GET'])
def get_farmer_chats():
    """Get all chats for farmer"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    farmer_id = session['farmer_id_verified']
    
    try:
        from models_marketplace_keep import Chat
        chats = Chat.query.filter_by(farmer_id=farmer_id, is_active=True).order_by(
            Chat.last_message_at.desc()
        ).all()
        
        chats_data = []
        for chat in chats:
            buyer = Buyer.query.get(chat.buyer_id)
            unread_count = sum(1 for msg in chat.messages if not msg.is_read and msg.sender_type == 'buyer')
            last_message = chat.messages[-1] if chat.messages else None
            
            chats_data.append({
                'chat_id': chat.id,
                'auction_id': chat.auction_id,
                'buyer_id': chat.buyer_id,
                'buyer_name': buyer.buyer_name if buyer else 'Unknown Buyer',
                'buyer_company': buyer.company_name if buyer else 'N/A',
                'crop_name': chat.crop_name,
                'unread_count': unread_count,
                'last_message': last_message.message if last_message else 'No messages yet',
                'last_message_time': last_message.created_at.isoformat() if last_message else None,
                'last_message_sender': last_message.sender_type if last_message else None,
                'updated_at': chat.updated_at.isoformat()
            })
        
        return jsonify({
            'chats': chats_data,
            'total': len(chats_data)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/chat/<chat_id>/messages', methods=['GET'])
def get_farmer_chat_messages(chat_id):
    """Get messages in a chat (farmer view)"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    farmer_id = session['farmer_id_verified']
    
    try:
        from models_marketplace_keep import Chat
        chat = Chat.query.get(chat_id)
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        if chat.farmer_id != farmer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Mark buyer messages as read
        for message in chat.messages:
            if message.sender_type == 'buyer' and not message.is_read:
                message.is_read = True
        db.session.commit()
        
        messages_data = [{
            'message_id': msg.id,
            'sender_type': msg.sender_type,
            'sender_name': msg.sender_name,
            'message': msg.message,
            'timestamp': msg.created_at.isoformat(),
            'is_read': msg.is_read
        } for msg in chat.messages]
        
        return jsonify({
            'chat_id': chat_id,
            'messages': messages_data,
            'total': len(messages_data)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/chat/<chat_id>/send', methods=['POST'])
def send_farmer_message(chat_id):
    """Send a message in chat (farmer)"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    farmer_id = session['farmer_id_verified']
    
    try:
        from models_marketplace_keep import Chat, ChatMessage
        chat = Chat.query.get(chat_id)
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        if chat.farmer_id != farmer_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        farmer = Farmer.query.get(farmer_id)
        message = ChatMessage(
            chat_id=chat_id,
            sender_type='farmer',
            sender_id=farmer_id,
            sender_name=farmer.name if farmer else 'Farmer',
            message=message_text,
            is_read=False
        )
        
        chat.last_message_at = datetime.utcnow()
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_id': message.id,
            'timestamp': message.created_at.isoformat()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== LEADERBOARD ENDPOINTS ====================

@bidding_bp.route('/farmer/leaderboard/activity', methods=['GET'])
def farmer_leaderboard_activity():
    """Get activity-based leaderboard (auctions and revenue)"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    farmer_id = session['farmer_id_verified']
    
    try:
        from sqlalchemy import func
        
        # Get all farmers with their auction stats
        farmers_stats = db.session.query(
            Farmer.id,
            Farmer.name,
            func.count(Auction.id).label('total_auctions'),
            func.sum(Auction.base_price_per_quintal * Auction.quantity_quintals).label('total_revenue')
        ).outerjoin(
            Auction, Farmer.id == Auction.farmer_id
        ).filter(
            Auction.status.in_(['completed', 'active'])
        ).group_by(
            Farmer.id, Farmer.name
        ).order_by(
            func.count(Auction.id).desc(),
            func.sum(Auction.base_price_per_quintal * Auction.quantity_quintals).desc()
        ).all()
        
        # Build leaderboard list
        leaderboard = []
        your_rank = 0
        your_auctions = 0
        your_revenue = 0
        your_data = None
        
        for idx, stat in enumerate(farmers_stats):
            farmer_entry = {
                'farmer_id': stat.id,
                'farmer_name': stat.name,
                'total_auctions': stat.total_auctions or 0,
                'total_revenue': float(stat.total_revenue) if stat.total_revenue else 0,
                'is_you': stat.id == farmer_id
            }
            leaderboard.append(farmer_entry)
            
            if stat.id == farmer_id:
                your_rank = idx + 1
                your_auctions = stat.total_auctions or 0
                your_revenue = float(stat.total_revenue) if stat.total_revenue else 0
                your_data = farmer_entry
        
        # If farmer not in list, add at bottom
        if not your_data:
            your_rank = len(leaderboard) + 1
            your_auctions = 0
            your_revenue = 0
            farmer = Farmer.query.get(farmer_id)
            leaderboard.append({
                'farmer_id': farmer_id,
                'farmer_name': farmer.name if farmer else 'Unknown',
                'total_auctions': 0,
                'total_revenue': 0,
                'is_you': True
            })
        
        # Calculate top 3 farmers
        top_3_auctions = leaderboard[2]['total_auctions'] if len(leaderboard) > 2 else leaderboard[0]['total_auctions']
        top_3_revenue = leaderboard[2]['total_revenue'] if len(leaderboard) > 2 else leaderboard[0]['total_revenue']
        
        auctions_to_top3 = max(0, top_3_auctions - your_auctions)
        revenue_to_top3 = max(0, top_3_revenue - your_revenue)
        
        # Calculate progress percentage (based on distance from top 3)
        if auctions_to_top3 > 0:
            max_gap = leaderboard[0]['total_auctions'] - top_3_auctions if leaderboard else 10
            progress = max(0, min(100, ((auctions_to_top3 - max_gap) / max(max_gap, 1)) * 100)) if max_gap > 0 else 100
        else:
            progress = 100
        
        # Get top crops for the farmer
        top_crops = db.session.query(
            Auction.crop_name,
            func.count(Auction.id).label('count')
        ).filter(
            Auction.farmer_id == farmer_id,
            Auction.status.in_(['completed', 'active'])
        ).group_by(
            Auction.crop_name
        ).order_by(
            func.count(Auction.id).desc()
        ).limit(3).all()
        
        top_crops_data = [
            {'crop_name': crop[0], 'count': crop[1]}
            for crop in top_crops
        ]
        
        # Calculate rank change (simplified - would need historical data for real implementation)
        rank_change = 0  # Default to no change
        
        return jsonify({
            'your_rank': your_rank,
            'total_farmers': len(leaderboard),
            'your_auctions': your_auctions,
            'your_revenue': your_revenue,
            'rank_change': rank_change,
            'auctions_to_top3': auctions_to_top3,
            'revenue_to_top3': revenue_to_top3,
            'progress_to_top3': progress,
            'top_crops': top_crops_data,
            'leaderboard': leaderboard[:50]  # Return top 50
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bidding_bp.route('/farmer/leaderboard/rewards', methods=['GET'])
def farmer_leaderboard_rewards():
    """Get rewards-based leaderboard (coins)"""
    if 'farmer_id_verified' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    farmer_id = session['farmer_id_verified']
    
    try:
        from sqlalchemy import func
        
        # For now, calculate coins based on completed auctions
        # In future, this will come from a Coins/Rewards table
        farmers_coins = db.session.query(
            Farmer.id,
            Farmer.name,
            func.count(Auction.id).label('completed_auctions'),
            (func.count(Auction.id) * 100).label('total_coins'),  # 100 coins per auction
            (func.count(Auction.id) * 100).label('coins_this_month')  # Simplified
        ).outerjoin(
            Auction, Farmer.id == Auction.farmer_id
        ).filter(
            Auction.status == 'completed'
        ).group_by(
            Farmer.id, Farmer.name
        ).order_by(
            (func.count(Auction.id) * 100).desc()
        ).all()
        
        # Build leaderboard list
        leaderboard = []
        your_rank = 0
        your_coins = 0
        your_coins_month = 0
        your_data = None
        
        for idx, stat in enumerate(farmers_coins):
            farmer_entry = {
                'farmer_id': stat.id,
                'farmer_name': stat.name,
                'total_coins': stat.total_coins or 0,
                'coins_this_month': stat.coins_this_month or 0,
                'is_you': stat.id == farmer_id
            }
            leaderboard.append(farmer_entry)
            
            if stat.id == farmer_id:
                your_rank = idx + 1
                your_coins = stat.total_coins or 0
                your_coins_month = stat.coins_this_month or 0
                your_data = farmer_entry
        
        # If farmer not in list, add at bottom
        if not your_data:
            your_rank = len(leaderboard) + 1
            your_coins = 0
            your_coins_month = 0
            farmer = Farmer.query.get(farmer_id)
            leaderboard.append({
                'farmer_id': farmer_id,
                'farmer_name': farmer.name if farmer else 'Unknown',
                'total_coins': 0,
                'coins_this_month': 0,
                'is_you': True
            })
        
        # Calculate top 1 target
        top_1_coins = leaderboard[0]['total_coins'] if leaderboard else your_coins
        coins_to_top1 = max(0, top_1_coins - your_coins)
        
        # Estimate weeks to top 1 based on current rate
        monthly_rate = max(your_coins_month, 100)  # At least 100 coins per month
        weeks_to_top1 = max(1, round(coins_to_top1 / (monthly_rate / 4)))
        
        # Calculate progress percentage
        if coins_to_top1 > 0:
            max_gap = leaderboard[0]['total_coins'] - (leaderboard[1]['total_coins'] if len(leaderboard) > 1 else 0) if leaderboard else 1000
            progress = max(0, min(100, ((coins_to_top1 - max_gap) / max(max_gap, 1)) * 100)) if max_gap > 0 else 100
        else:
            progress = 100
        
        # Earnings breakdown
        earnings_breakdown = [
            {'source': 'From Auctions', 'coins': max(0, your_coins - 300)},
            {'source': 'Scheme Bonus', 'coins': 150},
            {'source': 'Quality Premium', 'coins': 150}
        ]
        
        # Simplify based on actual coins
        if your_coins < 300:
            earnings_breakdown = [
                {'source': 'From Auctions', 'coins': your_coins},
                {'source': 'Scheme Bonus', 'coins': 0},
                {'source': 'Quality Premium', 'coins': 0}
            ]
        
        rank_change = 0  # Default to no change
        
        return jsonify({
            'your_rank': your_rank,
            'total_farmers': len(leaderboard),
            'your_coins': your_coins,
            'your_coins_this_month': your_coins_month,
            'rank_change': rank_change,
            'coins_to_top1': coins_to_top1,
            'weeks_to_top1': weeks_to_top1,
            'progress_to_top1': progress,
            'earnings_breakdown': earnings_breakdown,
            'leaderboard': leaderboard[:50]  # Return top 50
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== LEADERBOARD PAGE ROUTE ====================

@bidding_bp.route('/farmer/leaderboard')
def farmer_leaderboard_page():
    """View farmer leaderboard with activity and rewards tabs"""
    if 'farmer_id_verified' not in session:
        return redirect(url_for('auth.login'))
    
    farmer_id = session['farmer_id_verified']
    farmer = Farmer.query.get(farmer_id)
    
    if not farmer:
        return redirect(url_for('auth.login'))
    
    return render_template('farmer_leaderboard.html', farmer=farmer)
