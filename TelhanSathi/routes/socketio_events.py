"""
Socket.IO Event Handlers for Real-time Bidding System
Handles connections, disconnections, and real-time event broadcasting
"""

from flask_socketio import emit, join_room, leave_room, rooms
from flask import session, request
from datetime import datetime
import json

# Store connected users in memory
connected_users = {}

def register_socketio_events(socketio):
    """Register all Socket.IO event handlers"""
    
    # ===================== DEFAULT NAMESPACE HANDLERS =====================
    @socketio.on('connect', namespace='/')
    def handle_default_connect():
        """Handle default namespace connection"""
        try:
            print(f"[SOCKETIO] Client connected to default namespace: {request.sid}")
            # Just acknowledge the connection
            return True
        except Exception as e:
            print(f"[SOCKETIO ERROR] Default connect error: {str(e)}")
            return False
    
    @socketio.on('disconnect', namespace='/')
    def handle_default_disconnect():
        """Handle default namespace disconnection"""
        try:
            print(f"[SOCKETIO] Client disconnected from default namespace: {request.sid}")
        except Exception as e:
            print(f"[SOCKETIO ERROR] Default disconnect error: {str(e)}")
    
    # ===================== BIDDING NAMESPACE HANDLERS =====================
    @socketio.on('connect', namespace='/bidding')
    def handle_connect():
        """Handle buyer connection"""
        try:
            # Get buyer ID from session
            buyer_id = session.get('buyer_id_verified')
            farmer_id = session.get('farmer_id_verified')
            
            user_type = None
            user_id = None
            
            if buyer_id:
                user_type = 'buyer'
                user_id = buyer_id
            elif farmer_id:
                user_type = 'farmer'
                user_id = farmer_id
            
            if user_id:
                # Store connection info
                connected_users[user_id] = {
                    'sid': request.sid,
                    'user_type': user_type,
                    'connected_at': datetime.utcnow()
                }
                
                print(f"✅ {user_type.upper()} connected: {user_id}")
                print(f"📊 Total connected users now: {len(connected_users)}")
                
                # Emit connection confirmation
                emit('connection_response', {
                    'status': 'connected',
                    'user_type': user_type,
                    'user_id': user_id,
                    'message': f'Connected to bidding system as {user_type}'
                })
            else:
                print(f"⚠️ Anonymous connection attempt")
                emit('connection_response', {
                    'status': 'not_authenticated',
                    'message': 'Please login to access real-time bidding'
                })
        
        except Exception as e:
            print(f"❌ Connection error: {str(e)}")
            emit('error', {
                'message': 'Connection failed',
                'error': str(e)
            })
    
    
    @socketio.on('disconnect', namespace='/bidding')
    def handle_disconnect():
        """Handle user disconnection"""
        try:
            # Find and remove user from connected_users
            user_to_remove = None
            for user_id, info in connected_users.items():
                if info['sid'] == request.sid:
                    user_to_remove = user_id
                    break
            
            if user_to_remove:
                user_type = connected_users[user_to_remove]['user_type']
                del connected_users[user_to_remove]
                print(f"👋 {user_type.upper()} disconnected")
                print(f"📊 Total connected users now: {len(connected_users)}")
        
        except Exception as e:
            print(f"❌ Disconnection error: {str(e)}")
    
    
    @socketio.on('join_auction', namespace='/bidding')
    def handle_join_auction(data):
        """Handle buyer joining an auction room"""
        try:
            auction_id = data.get('auction_id')
            buyer_id = session.get('buyer_id_verified')
            
            if not auction_id or not buyer_id:
                emit('error', {'message': 'Invalid auction or not authenticated'})
                return
            
            room_name = f'auction_{auction_id}'
            join_room(room_name)
        
        except Exception as e:
            print(f"❌ Join auction error: {str(e)}")
            emit('error', {'message': str(e)})
    
    
    @socketio.on('leave_auction', namespace='/bidding')
    def handle_leave_auction(data):
        """Handle buyer leaving an auction room"""
        try:
            auction_id = data.get('auction_id')
            buyer_id = session.get('buyer_id_verified')
            
            if not auction_id or not buyer_id:
                return
            
            room_name = f'auction_{auction_id}'
            leave_room(room_name)
        
        except Exception as e:
            print(f"❌ Leave auction error: {str(e)}")


def broadcast_auction_created(auction_data):
    """
    Broadcast new auction to all connected buyers
    """
    try:
        from extensions import socketio as sio
        
        auction_id = auction_data.get('auction_id')
        crop_name = auction_data.get('crop_name')
        farmer_name = auction_data.get('farmer_name')
        
        # Emit to ALL connected clients in /bidding namespace
        sio.emit('auction_created', auction_data, namespace='/bidding')
        
        print(f"📢 New auction broadcast: {crop_name} by {farmer_name}")
        print(f"📊 Reached {len(connected_users)} connected users")
        
    except Exception as e:
        print(f"❌ Error in broadcast_auction_created: {str(e)}")


def broadcast_bid_placed(auction_id, bid_data):
    """
    Broadcast bid to all connected users (buyers + farmer watching this auction)
    """
    try:
        from extensions import socketio as sio
        
        # Emit to ALL connected clients in /bidding namespace
        # This reaches all buyers and the farmer
        bid_payload = {
            'auction_id': auction_id,
            'highest_bid': bid_data.get('highest_bid'),
            'bid_price_per_quintal': bid_data.get('bid_price_per_quintal'),
            'bid_total_amount': bid_data.get('bid_total_amount'),
            'buyer_count': bid_data.get('buyer_count'),
            'minimum_bid_increment': bid_data.get('minimum_bid_increment'),
            'minimum_bid_required': bid_data.get('minimum_bid_required')
        }
        
        sio.emit('bid_placed', bid_payload, namespace='/bidding')
        print(f"📢 New bid broadcast for auction: {auction_id} at ₹{bid_data.get('bid_price_per_quintal')}/q")
        
    except Exception as e:
        print(f"❌ Error in broadcast_bid_placed: {str(e)}")


def broadcast_counter_offer_sent(co_data):
    """
    Broadcast counter offer to buyer in real-time
    """
    try:
        from extensions import socketio as sio
        
        # Emit to buyer and all connected clients
        co_payload = {
            'event_type': 'counter_offer_sent',
            'auction_id': co_data.get('auction_id'),
            'counter_offer_id': co_data.get('counter_offer_id'),
            'bid_id': co_data.get('bid_id'),
            'buyer_id': co_data.get('buyer_id'),
            'counter_price': co_data.get('counter_price'),
            'farmer_name': co_data.get('farmer_name'),
            'crop_name': co_data.get('crop_name'),
            'quantity': co_data.get('quantity')
        }
        
        sio.emit('counter_offer_event', co_payload, namespace='/bidding')
        print(f"📢 Counter offer broadcast for auction: {co_data.get('auction_id')} at ₹{co_data.get('counter_price')}/q")
        
    except Exception as e:
        print(f"❌ Error in broadcast_counter_offer_sent: {str(e)}")


def broadcast_counter_offer_response(response_data):
    """
    Broadcast counter offer acceptance/rejection to farmer in real-time
    """
    try:
        from extensions import socketio as sio
        
        # Emit to farmer and all connected clients
        response_payload = {
            'event_type': 'counter_offer_response',
            'auction_id': response_data.get('auction_id'),
            'counter_offer_id': response_data.get('counter_offer_id'),
            'bid_id': response_data.get('bid_id'),
            'buyer_id': response_data.get('buyer_id'),
            'status': response_data.get('status'),
            'counter_price': response_data.get('counter_price'),
            'crop_name': response_data.get('crop_name')
        }
        
        sio.emit('counter_offer_event', response_payload, namespace='/bidding')
        print(f"📢 Counter offer {response_data.get('status')} broadcast for auction: {response_data.get('auction_id')}")
        
    except Exception as e:
        print(f"❌ Error in broadcast_counter_offer_response: {str(e)}")


def broadcast_bid_accepted(auction_data):
    """
    Broadcast bid acceptance to all connected buyers (auction completed)
    """
    try:
        from extensions import socketio as sio
        
        # Emit to all buyers connected to the /bidding namespace
        acceptance_payload = {
            'event_type': 'bid_accepted',
            'auction_id': auction_data.get('auction_id'),
            'bid_id': auction_data.get('bid_id'),
            'winning_buyer_id': auction_data.get('winning_buyer_id'),
            'winning_price': auction_data.get('winning_price'),
            'crop_name': auction_data.get('crop_name'),
            'farmer_name': auction_data.get('farmer_name'),
            'quantity': auction_data.get('quantity')
        }
        
        sio.emit('bid_event', acceptance_payload, namespace='/bidding')
        print(f"📢 Bid accepted broadcast for auction: {auction_data.get('auction_id')} at ₹{auction_data.get('winning_price')}/Q")
        
    except Exception as e:
        print(f"❌ Error in broadcast_bid_accepted: {str(e)}")


def broadcast_auction_extended(extend_data):
    """
    Broadcast auction extension to all connected buyers
    """
    try:
        from extensions import socketio as sio
        
        extend_payload = {
            'event_type': 'auction_extended',
            'auction_id': extend_data.get('auction_id'),
            'new_end_time': extend_data.get('new_end_time'),
            'additional_hours': extend_data.get('additional_hours'),
            'crop_name': extend_data.get('crop_name'),
            'farmer_name': extend_data.get('farmer_name')
        }
        
        sio.emit('auction_event', extend_payload, namespace='/bidding')
        print(f"📢 Auction extended broadcast for auction: {extend_data.get('auction_id')} by {extend_data.get('additional_hours')} hours")
        
    except Exception as e:
        print(f"❌ Error in broadcast_auction_extended: {str(e)}")


def broadcast_auction_price_updated(price_data):
    """
    Broadcast auction minimum price update to all connected buyers
    """
    try:
        from extensions import socketio as sio
        
        price_payload = {
            'event_type': 'auction_price_updated',
            'auction_id': price_data.get('auction_id'),
            'new_minimum_price': price_data.get('new_minimum_price'),
            'crop_name': price_data.get('crop_name'),
            'farmer_name': price_data.get('farmer_name')
        }
        
        sio.emit('auction_event', price_payload, namespace='/bidding')
        print(f"📢 Auction price updated broadcast for auction: {price_data.get('auction_id')} to ₹{price_data.get('new_minimum_price')}/Q")
        
    except Exception as e:
        print(f"❌ Error in broadcast_auction_price_updated: {str(e)}")


def broadcast_auction_cancelled(cancel_data):
    """
    Broadcast auction cancellation to all connected buyers
    """
    try:
        from extensions import socketio as sio
        
        cancel_payload = {
            'event_type': 'auction_cancelled',
            'auction_id': cancel_data.get('auction_id'),
            'crop_name': cancel_data.get('crop_name'),
            'farmer_name': cancel_data.get('farmer_name')
        }
        
        sio.emit('auction_event', cancel_payload, namespace='/bidding')
        print(f"📢 Auction cancelled broadcast for auction: {cancel_data.get('auction_id')}")
        
    except Exception as e:
        print(f"❌ Error in broadcast_auction_cancelled: {str(e)}")
