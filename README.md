# Telhan Sathi 🌾

### Making Oilseed Farming Smarter, Safer, and More Profitable

**SIH 2025 | Problem Statement 1604 | Agriculture, FoodTech & Rural Development**

---

## Project Overview

Telhan Sathi (तेलहन साथी) is a digital agri-platform connecting farmers and buyers through real-time auctions, market intelligence, and assisted decision support.
It helps farmers move from uncertainty to better pricing outcomes with a practical, field-ready workflow.

---

## Key Features

### Marketplace & Trading
- **Real-time auctions (Nilami)** with live bidding updates
- **Buyer-farmer direct connection** without middlemen dependency
- **Bid management** with accept/reject and negotiation flow
- **Auction tracking** for active, completed, and won bids

### Farmer Productivity
- **Crop economics dashboard** for yield-cost-profit comparison
- **Weather + field monitoring** with actionable farm alerts
- **Subsidy discovery module** for scheme awareness and planning
- **Redemption store** with coin-based engagement and rewards

### Buyer Experience
- **Auction discovery** with clear listing details
- **Quick bidding flow** with real-time status visibility
- **Direct chat with farmers** for faster deal closure
- **Bid history and dashboard insights** for purchase planning

### Platform Foundation
- **Role-based onboarding** (farmer/buyer/admin)
- **OTP-enabled authentication flow**
- **Socket-based real-time communication**
- **Responsive web interface** for demo-friendly usage

---

## AI / Smart Features

- **AI-driven profitability guidance** integrated in product flows
- **Conceptual ARIMA-based forecasting support** for price trend insights
- **Smart recommendations** for crop choice and timing decisions

> Note: AI/ML assets are conceptually integrated. Heavy model and dataset artifacts are excluded from this lightweight repository version.

---

## Tech Stack

| Layer | Stack |
| --- | --- |
| Backend | Flask, SQLAlchemy, Flask Blueprints |
| Frontend | HTML5, CSS3, JavaScript, Bootstrap |
| Database | SQLite (dev), PostgreSQL-ready |
| Real-time | Flask-SocketIO |
| AI/Smart Layer | Python-based integrated logic (lightweight repo mode) |
| Integrations | Weather APIs, Translation APIs, IoT-ready endpoints |
| Deployment | Render, Gunicorn/Werkzeug-compatible setup |

---

## Screenshots

### Farmer Interface

**Home Dashboard**
Farmer landing page with quick actions and module access.
![Home Page](documents/screenshots/home%20page.jpeg)

**Auction Dashboard**
Manage live auctions, bids, and outcomes in one view.
![Bidding Dashboard Farmer](documents/screenshots/bidding%20dashboard%20farmer.jpeg)

**Auction Details**
Track reserve price, bid timeline, and buyer activity.
![Auction Details Modal](documents/screenshots/bid%20details%20page%20farmer.jpeg)

**Winning Bid Summary**
Clear closure details after successful auction completion.
![Winning Bid Details](documents/screenshots/winning%20bid%20details%20page%20farmer.jpeg)

**Profit Simulator**
Compare projected outcomes for oilseed vs alternative crops.
![Profit Simulator](documents/screenshots/profit%20simulator%20page%20farmer.jpeg)

**Crop Economics**
Analyze crop-level cost, demand, and profitability trends.
![Crop Economics](documents/screenshots/crop%20economics%20page%20farmer.jpeg)

**12-Month Trend View**
Long-range crop economics perspective for planning decisions.
![Crop Economics Trends](documents/screenshots/detailed%20crop%20economics%20page%20with%2012%20months%20trend%20farmer.jpeg)

**Subsidies & Schemes**
Explore relevant government support opportunities.
![Subsidies Page](documents/screenshots/schemes%20and%20subsides%20page%20farmer.jpeg)

**Redemption Store**
Redeem earned coins for useful products and services.
![Redemption Store](documents/screenshots/redeemption%20store%20page%20farmer.jpeg)

**Farmer Chat**
Real-time communication for faster negotiation and trust.
![Chat with Farmer](documents/screenshots/chat%20with%20farmer%20page%20buyer.jpeg)

### Buyer Interface

**Buyer Dashboard**
Centralized bidding activity and purchase overview.
![Buyer Dashboard](documents/screenshots/bidding%20dashboard%20buyer.jpeg)

**Auction Exploration**
Review listing details before placing bids.
![View Auction Details](documents/screenshots/view%20auction%20details%20modal%20buyer.jpeg)

**My Bids**
Track bid status, negotiation updates, and outcomes.
![My Bids Page](documents/screenshots/mybids%20page%20buyer.jpeg)

**Buyer-Farmer Chat**
Direct messaging streamlines discussion and conversion.
![Chat with Farmer Buyer](documents/screenshots/chat%20with%20farmer%20page%20buyer.jpeg)

---

## Project Structure

```text
TelhanSathi-SIH2025/
├── README.md
├── documents/
│   └── screenshots/
└── TelhanSathi/
    ├── app.py
    ├── models.py
    ├── routes/
    ├── templates/
    └── static/
```

---

## Setup Instructions

### Prerequisites
- Python 3.8+
- pip
- Git

### Run Locally

```bash
# 1) Clone
git clone https://github.com/VishalGhuge111/TelhanSathi-SIH2025.git
cd TelhanSathi-SIH2025/TelhanSathi

# 2) Create and activate virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Set environment variables in .env
# SECRET_KEY=your-secret-key
# DATABASE_URL=sqlite:///telhan_sathi.db
# GOOGLE_API_KEY=your-google-api-key

# 5) Initialize database
python init_db.py

# 6) Start app
python app.py
```

Open: `http://localhost:5000`

---

## Team

**Algo Sapiens**

- **Dhiraj Durgade** - Backend architecture and core platform logic
- **Harsh** - Blockchain integration concepts
- **Ujjwal** - AI/ML strategy and forecasting logic
- **Vishal** - Frontend experience and dashboard design
- **Janhvi** - Frontend components and responsiveness
- **Naman** - IoT integration support
- **Nisarg Wath (Mentor)** - Technical guidance and review

---

## Vision

Telhan Sathi aims to become the operating layer for profitable oilseed farming by combining transparent market access, actionable intelligence, and farmer-first digital workflows.

**Built for SIH 2025. Designed for real rural impact.**
