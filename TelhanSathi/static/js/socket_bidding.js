/**
 * Socket.IO Client for Real-time Bidding System
 * SIMPLIFIED VERSION - Focus on working, not complexity
 */

console.log('🚀 [SOCKETIO] Script loading...');

// Wait for page to be ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 [SOCKETIO] Page ready, connecting...');
    
    // Initialize Socket.IO connection
    try {
        const socket = io('/bidding', {
            reconnection: true,
            reconnection_delay: 1000,
            reconnection_delay_max: 5000,
            reconnection_attempts: 5,
            transports: ['websocket', 'polling']
        });

        socket.on('connect', function() {
            console.log('✅ [SOCKETIO] CONNECTED - Socket ID:', socket.id);
        });

        socket.on('connection_response', function(data) {
            console.log('✅ [SOCKETIO] SERVER RESPONSE:', data);
        });

        socket.on('auction_created', function(auctionData) {
            console.log('🎯 [SOCKETIO] NEW AUCTION EVENT RECEIVED:', auctionData);
            
            // Call handler if it exists
            if (window.handleNewAuctionReceived && typeof window.handleNewAuctionReceived === 'function') {
                console.log('📢 [SOCKETIO] Calling handleNewAuctionReceived...');
                window.handleNewAuctionReceived(auctionData);
            } else {
                console.warn('⚠️ [SOCKETIO] handleNewAuctionReceived NOT FOUND - Not on auction page?');
            }
        });

        socket.on('bid_placed', function(bidData) {
            console.log('💰 [SOCKETIO] NEW BID EVENT RECEIVED:', bidData);
            
            // Call handler if it exists
            if (window.handleBidUpdate && typeof window.handleBidUpdate === 'function') {
                console.log('💬 [SOCKETIO] Calling handleBidUpdate...');
                window.handleBidUpdate(bidData);
            }
        });

        socket.on('counter_offer_event', function(counterOfferData) {
            console.log('🔔 [SOCKETIO] COUNTER OFFER EVENT RECEIVED:', counterOfferData);
            
            // Call handler if it exists
            if (window.handleCounterOfferUpdate && typeof window.handleCounterOfferUpdate === 'function') {
                console.log('💬 [SOCKETIO] Calling handleCounterOfferUpdate...');
                window.handleCounterOfferUpdate(counterOfferData);
            }
        });

        socket.on('bid_event', function(bidData) {
            console.log('✅ [SOCKETIO] BID ACCEPTANCE EVENT RECEIVED:', bidData);
            
            // Call handler if it exists
            if (window.handleBidAccepted && typeof window.handleBidAccepted === 'function') {
                console.log('💬 [SOCKETIO] Calling handleBidAccepted...');
                window.handleBidAccepted(bidData);
            }
        });

        socket.on('auction_event', function(auctionData) {
            console.log('🎯 [SOCKETIO] AUCTION EVENT RECEIVED:', auctionData);
            
            // Call appropriate handler based on event type
            const eventType = auctionData.event_type;
            
            if (eventType === 'auction_extended' && window.handleAuctionExtended && typeof window.handleAuctionExtended === 'function') {
                console.log('💬 [SOCKETIO] Calling handleAuctionExtended...');
                window.handleAuctionExtended(auctionData);
            } else if (eventType === 'auction_price_updated' && window.handleAuctionPriceUpdated && typeof window.handleAuctionPriceUpdated === 'function') {
                console.log('💬 [SOCKETIO] Calling handleAuctionPriceUpdated...');
                window.handleAuctionPriceUpdated(auctionData);
            } else if (eventType === 'auction_cancelled' && window.handleAuctionCancelled && typeof window.handleAuctionCancelled === 'function') {
                console.log('💬 [SOCKETIO] Calling handleAuctionCancelled...');
                window.handleAuctionCancelled(auctionData);
            }
        });

        socket.on('disconnect', function() {
            console.log('❌ [SOCKETIO] DISCONNECTED');
        });

        socket.on('error', function(error) {
            console.error('❌ [SOCKETIO] ERROR:', error);
        });

    } catch (error) {
        console.error('❌ [SOCKETIO] FATAL ERROR:', error);
    }
});

console.log('🚀 [SOCKETIO] Script loaded and waiting for page...');
