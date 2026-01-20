# 🤖 AI Trading Bot

Automated trading system with AI-powered entry and guardian logic for XAUUSD on MetaTrader 5.

![Dashboard Preview](https://via.placeholder.com/800x400?text=AI+Trading+Dashboard)

## ✨ Features

- **AI Entry Logic** - Analyzes market structure to find optimal entry points
- **AI Guardian Logic** - Monitors positions and manages risk in real-time
- **Auto Break-Even** - Moves SL to entry price after X pips profit
- **Session Filter** - Trade only during preferred sessions (London, NY, Asia, Sydney)
- **Trailing Stop** - Automatically trail stop loss to lock in profits
- **Real-time Dashboard** - WebSocket-powered live updates
- **Manual Controls** - Place trades manually or let AI decide

## 🚀 Quick Start

### Prerequisites

1. **MetaTrader 5** - Install and run on your PC
2. **Python 3.10+** - [Download Python](https://python.org)
3. **Node.js 18+** - [Download Node.js](https://nodejs.org)
4. **Groq API Key (FREE)** - [Get it here](https://console.groq.com)

### Setup

1. **Clone and setup environment**

   ```bash
   cd c:\Users\faris\OneDrive\Desktop\autocut
   copy .env.example .env
   ```

2. **Edit `.env` with your credentials**

   ```env
   MT5_LOGIN=your_account_number
   MT5_PASSWORD=your_password
   MT5_SERVER=YourBroker-Server
   GROQ_API_KEY=your_groq_api_key
   ```

3. **Install Backend Dependencies**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Install Frontend Dependencies**

   ```bash
   cd frontend
   npm install
   ```

### Running the Application

**Terminal 1 - Start Backend:**

```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Start Frontend:**

```bash
cd frontend
npm run dev
```

**Open Dashboard:** <http://localhost:5173>

## 📁 Project Structure

```
autocut/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── mt5_client.py        # MT5 operations
│   ├── ai_brain.py          # AI logic (Groq/Deepseek)
│   ├── trading_engine.py    # Main trading loop
│   ├── websocket_manager.py # Real-time updates
│   ├── config.py            # Configuration
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── components/
│   │       ├── StatusPanel.jsx
│   │       ├── PositionsTable.jsx
│   │       ├── AIReasoningFeed.jsx
│   │       ├── ConfigPanel.jsx
│   │       └── ConnectionModal.jsx
│   └── package.json
│
├── .env.example
└── README.md
```

## 🎯 How It Works

### AI Entry Logic

1. Fetches H1 and M15 candle data
2. Analyzes market structure (trend, S/R zones)
3. Waits for high-probability setup (min R:R 1.5:1)
4. Places order with calculated SL/TP

### AI Guardian Logic

1. Monitors each open position
2. Evaluates market conditions
3. Actions: HOLD, MODIFY_SL, MODIFY_TP, or CLOSE
4. Implements auto-BEP and trailing stop

## 🔧 Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| Lot Size | Volume per trade | 0.01 |
| Max Positions | Maximum open positions | 3 |
| Risk % | Risk per trade | 1% |
| Min R:R | Minimum risk/reward | 1.5 |
| Auto-BEP | Break-even trigger | 5 pips |
| Trailing Stop | Trail distance | 10 pips |

## ⚠️ Disclaimer

This bot is for **educational purposes only**. Trading involves significant risk of loss. Always test with a **demo account** first. The developers are not responsible for any financial losses.

## 📝 License

MIT License - Use at your own risk.
