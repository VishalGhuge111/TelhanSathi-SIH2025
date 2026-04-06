"""
Bidding System Models
Contains models for: Auction, Bid, CounterOffer, AuctionNotification
Marketplace models (CropListing, SellRequest, BuyerOffer, etc.) have been removed
"""

import uuid
from datetime import datetime
from extensions import db


# ===== BUYER MODEL (KEPT FOR BIDDING SYSTEM) =====

class Buyer(db.Model):
    """Buyer model for bidding system - stores buyer profile and credentials"""
    __tablename__ = "buyers"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Login credentials
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    
    # Profile information
    buyer_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    company_name = db.Column(db.String(255))
    address = db.Column(db.String(500))
    
    # Location information
    location = db.Column(db.String(255))
    district = db.Column(db.String(100))
    state = db.Column(db.String(100), default='Maharashtra')
    
    # Account status
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - only for bidding
    bids = db.relationship('Bid', backref='buyer', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Buyer {self.buyer_name} - {self.email}>'


# ===== CHAT MODELS (KEPT FOR COMMUNICATION) =====

class Chat(db.Model):
    """Chat conversations between buyers and farmers"""
    __tablename__ = "chats"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Participants
    buyer_id = db.Column(db.String(36), db.ForeignKey("buyers.id"), nullable=False)
    farmer_id = db.Column(db.String(36), db.ForeignKey("farmers.id"), nullable=False)
    
    # Context
    auction_id = db.Column(db.String(36), db.ForeignKey("auctions.id"), nullable=True)
    
    crop_name = db.Column(db.String(100), nullable=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = db.relationship("ChatMessage", backref="chat", cascade="all,delete", lazy=True)


class ChatMessage(db.Model):
    """Individual chat messages"""
    __tablename__ = "chat_messages"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = db.Column(db.String(36), db.ForeignKey("chats.id"), nullable=False)
    
    sender_type = db.Column(db.String(10), nullable=False)  # 'buyer' or 'farmer'
    sender_id = db.Column(db.String(36), nullable=False)
    sender_name = db.Column(db.String(255))
    
    message = db.Column(db.Text, nullable=False)
    
    is_read = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ===== REAL-TIME BIDDING SYSTEM (NILAMI) =====

class Auction(db.Model):
    """Auction model - represents farmer's oilseed auction"""
    __tablename__ = "auctions"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Farmer info
    farmer_id = db.Column(db.String(36), db.ForeignKey('farmers.id'), nullable=False, index=True)
    
    # Auction details
    crop_name = db.Column(db.String(100), nullable=False)  # e.g., "Mustard", "Groundnut"
    quantity_quintals = db.Column(db.Float, nullable=False)
    quality_grade = db.Column(db.String(50), default='Standard')  # A, B, C, Standard
    
    # Pricing
    base_price_per_quintal = db.Column(db.Float, nullable=False)  # Starting price
    minimum_bid_increment = db.Column(db.Float, default=50)  # Min increase per bid
    current_highest_bid = db.Column(db.Float)  # Current highest bid
    
    # Auction timeline
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    
    # Status
    status = db.Column(db.String(50), default='active')  # active, closed, cancelled, completed
    
    # Location & Logistics
    location = db.Column(db.String(255), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), default='Maharashtra')
    
    # Additional info
    description = db.Column(db.Text)
    harvest_date = db.Column(db.Date)
    storage_location = db.Column(db.String(255))
    
    # Photos of oilseed harvest
    photo1_path = db.Column(db.String(255))
    photo2_path = db.Column(db.String(255))
    photo3_path = db.Column(db.String(255))
    photo4_path = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bids = db.relationship('Bid', backref='auction', lazy=True, cascade='all, delete-orphan')
    counter_offers = db.relationship('CounterOffer', backref='auction', lazy=True, cascade='all, delete-orphan')
    farmer = db.relationship('Farmer', backref='auctions', lazy=True)
    
    def __repr__(self):
        return f'<Auction {self.crop_name} by Farmer {self.farmer_id}>'


class Bid(db.Model):
    """Bid model - represents a buyer's bid on an auction"""
    __tablename__ = "bids"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Auction & Buyer info
    auction_id = db.Column(db.String(36), db.ForeignKey('auctions.id'), nullable=False, index=True)
    buyer_id = db.Column(db.String(36), db.ForeignKey('buyers.id'), nullable=False, index=True)
    
    # Bid amount
    bid_price_per_quintal = db.Column(db.Float, nullable=False)
    bid_total_amount = db.Column(db.Float, nullable=False)  # bid_price * quantity
    
    # Status
    status = db.Column(db.String(50), default='active')  # active, accepted, rejected, expired
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Bid by {self.buyer_id} @ ₹{self.bid_price_per_quintal}/quintal>'


class CounterOffer(db.Model):
    """Counter offer model - farmer's counter to a buyer's bid"""
    __tablename__ = "counter_offers"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Auction & Bid info
    auction_id = db.Column(db.String(36), db.ForeignKey('auctions.id'), nullable=False, index=True)
    bid_id = db.Column(db.String(36), db.ForeignKey('bids.id'), nullable=False, index=True)
    buyer_id = db.Column(db.String(36), db.ForeignKey('buyers.id'), nullable=False, index=True)
    
    # Counter offer price
    counter_price_per_quintal = db.Column(db.Float, nullable=False)
    
    # Status
    status = db.Column(db.String(50), default='pending')  # pending, accepted, rejected, expired
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<CounterOffer @ ₹{self.counter_price_per_quintal}/quintal>'


class AuctionNotification(db.Model):
    """Notifications for auction events"""
    __tablename__ = "auction_notifications"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # User info (farmer or buyer)
    user_id = db.Column(db.String(36), nullable=False, index=True)
    user_type = db.Column(db.String(50))  # 'farmer' or 'buyer'
    
    # Auction info
    auction_id = db.Column(db.String(36), db.ForeignKey('auctions.id'), nullable=False, index=True)
    
    # Notification
    notification_type = db.Column(db.String(50))  # new_bid, counter_offer, auction_closed, etc
    message = db.Column(db.Text)
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AuctionNotification {self.notification_type} for {self.user_id}>'
