# StockCall Tracker — Full Deployment Guide

## Project Structure

```
stockcall/
├── backend/
│   ├── app.py                  ← Flask entry point
│   ├── database.py             ← SQLite schema + init
│   ├── requirements.txt
│   ├── routes/
│   │   ├── calls.py            ← /api/calls
│   │   ├── brokers.py          ← /api/brokers
│   │   ├── analytics.py        ← /api/analytics  /api/prices  /api/alerts  /api/import
│   └── services/
│       ├── parser.py           ← Message/WhatsApp/Telegram/PDF/CSV parser
│       ├── price_fetcher.py    ← yfinance price fetcher with caching
│       └── analytics.py        ← Broker scoring + analytics queries
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── api.js              ← API client
│   │   └── (React components)
└── docs/
    └── DEPLOY.md               ← This file
```

---

## 1. Backend Setup (Python / Flask)

### Prerequisites
- Python 3.10+
- pip

### Step-by-step

```bash
# Clone / navigate to project
cd stockcall/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Set environment variables
export FLASK_DEBUG=true
export DATABASE_URL=stockcall.db
export SECRET_KEY=your-secret-key-here

# Run the server
python app.py
```

Server starts at: **http://localhost:5000**

Health check: `curl http://localhost:5000/api/health`

---

## 2. Frontend Setup (React + Vite)

### Prerequisites
- Node.js 18+
- npm or yarn

### Step-by-step

```bash
cd stockcall/frontend

# Install dependencies
npm install

# Set API URL (create .env file)
echo "VITE_API_URL=http://localhost:5000/api" > .env

# Start dev server
npm run dev
```

Frontend runs at: **http://localhost:5173**

---

## 3. API Endpoints Reference

### Calls  `/api/calls`
| Method | Path             | Description                          |
|--------|------------------|--------------------------------------|
| GET    | /                | List calls (supports filters)        |
| POST   | /                | Create new call                      |
| GET    | /:id             | Get single call                      |
| PUT    | /:id             | Update call (status, fields)         |
| DELETE | /:id             | Delete call                          |
| POST   | /parse           | Parse raw message → structured data  |

**Filter params:** `broker`, `call_type`, `status`, `stock`, `action`, `start_date`, `end_date`, `limit`, `offset`

### Brokers  `/api/brokers`
| Method | Path             | Description                          |
|--------|------------------|--------------------------------------|
| GET    | /                | List all active brokers              |
| POST   | /                | Create broker                        |
| PUT    | /:id             | Update broker                        |
| DELETE | /:id             | Deactivate broker                    |
| POST   | /:id/rescore     | Recompute AI reliability score       |

### Analytics  `/api/analytics`
| Method | Path             | Description                          |
|--------|------------------|--------------------------------------|
| GET    | /dashboard       | Overall stats summary                |
| GET    | /brokers         | Broker-wise performance table        |
| GET    | /by-type         | Accuracy by Intraday/Swing/etc.      |
| GET    | /monthly         | Month-by-month P&L                   |
| GET    | /rr              | Risk-reward analysis                 |
| GET    | /top-stocks      | Best performing stocks               |
| POST   | /rescore-all     | Recompute all broker scores          |

### Prices  `/api/prices`
| Method | Path               | Description                        |
|--------|--------------------|------------------------------------|
| GET    | /:symbol           | Get live price (NSE/BSE)           |
| POST   | /bulk              | Bulk price fetch                   |
| GET    | /history/:symbol   | Historical OHLCV data              |
| POST   | /update-statuses   | Auto-update Pending calls vs price |

### Import  `/api/import`
| Method | Path               | Description                         |
|--------|---------------------|-------------------------------------|
| POST   | /parse-message      | Parse single message (no DB write)  |
| POST   | /whatsapp           | Upload WhatsApp .txt export         |
| POST   | /telegram           | Upload Telegram result.json         |
| POST   | /csv                | Upload CSV file                     |
| POST   | /excel              | Upload .xlsx / .xls file            |
| POST   | /pdf                | Upload PDF research report          |
| POST   | /bulk-save          | Batch insert parsed calls           |

### Alerts  `/api/alerts`
| Method | Path       | Description                             |
|--------|------------|-----------------------------------------|
| GET    | /          | List all alerts                         |
| POST   | /check     | Check prices and fire triggered alerts  |
| DELETE | /:id       | Remove alert                            |

---

## 4. Database Schema Summary

```sql
brokers         -- Broker profiles + reliability score
stock_calls     -- All recommendation calls
call_outcomes   -- Exit price + P&L per call
price_cache     -- 5-min cached prices from yfinance
alerts          -- Target/SL price alerts per call
import_log      -- History of file imports
```

Full schema in `backend/database.py` → `SCHEMA_SQL`

---

## 5. Import Formats

### WhatsApp Export
1. Open WhatsApp group/chat → ⋮ → More → Export chat → Without Media
2. Upload the `.txt` file to `/api/import/whatsapp`

### Telegram Export
1. Open Desktop app → group → ⋮ → Export Chat History
2. Format: JSON, uncheck media
3. Upload `result.json` to `/api/import/telegram`

### CSV Format
Supported column names (case-insensitive):

| Your Column     | Maps To       |
|-----------------|---------------|
| Stock / Symbol  | stock         |
| Buy/Sell        | action        |
| Entry / Price   | entry_price   |
| Target / TGT    | target1       |
| Target2 / TGT2  | target2       |
| SL / Stoploss   | stoploss      |
| Date            | call_date     |
| Broker          | broker_name   |
| Type            | call_type     |
| Message / Notes | original_msg  |

### Excel
Same as CSV — supports `.xlsx` and `.xls`

### PDF
Automatically splits research reports into individual call blocks.
Works best with reports that have lines starting with BUY/SELL/ACCUMULATE.

---

## 6. Live Price Integration

Uses **yfinance** (Yahoo Finance) which is free and supports NSE/BSE:

- NSE symbols: `RELIANCE.NS`, `HDFCBANK.NS`
- BSE symbols: `500325.BO`

**Auto-status updater:**
```bash
# Call this endpoint every 5 minutes during market hours
curl -X POST http://localhost:5000/api/prices/update-statuses
```

Or set up a cron job:
```cron
*/5 9-15 * * 1-5  curl -X POST http://localhost:5000/api/prices/update-statuses
```

---

## 7. Production Deployment

### Option A: Local / Home Server

```bash
# Backend with gunicorn
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"

# Frontend build
cd frontend && npm run build
# Serve dist/ folder with nginx or serve
npx serve dist -p 3000
```

### Option B: Docker

```dockerfile
# Dockerfile.backend
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

```yaml
# docker-compose.yml
version: "3.9"
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.backend
    ports: ["5000:5000"]
    volumes: ["./data:/app/data"]
    environment:
      - DATABASE_URL=/app/data/stockcall.db
  frontend:
    build: ./frontend
    ports: ["3000:80"]
    depends_on: [backend]
```

### Option C: Railway / Render (Free cloud)

1. Push to GitHub
2. Connect repo to [railway.app](https://railway.app) or [render.com](https://render.com)
3. Set environment variable: `DATABASE_URL=stockcall.db`
4. Deploy → get public URL

---

## 8. Broker Reliability Score — Formula

The AI-based score (0–100) is computed as:

```
Score = Accuracy(40%) + RR_Score(25%) + Consistency(20%) + Drawdown(15%)

Accuracy    = (Target Hits + Partial) / Closed Calls × 100
RR_Score    = Avg(Reward/Risk ratio) / 3 × 100  [capped at 100]
Consistency = 100 − StdDev(P&L%) × 5
Drawdown    = 100 − (Max SL streak) × 15
```

Rescore endpoint: `POST /api/brokers/:id/rescore`
Rescore all: `POST /api/analytics/rescore-all`

---

## 9. Message Parser — Supported Formats

The regex+NLP parser handles all these formats:

```
# Format 1 — TradeBulls style
TRADEBULLS SECURITIES
TATA STEEL
CMP 202
TARGET 236
SUPPORT 211
DURATION 2-3 DAYS

# Format 2 — One-liner BUY
BUY RELIANCE ABOVE 1450
TARGET 1510 / 1540
STOPLOSS 1420
INTRADAY

# Format 3 — HDFC Accumulate
HDFC SECURITIES:
ACCUMULATE INFY
TARGET 1820
SL 1710
TIME 1 WEEK

# Format 4 — Compact
HDFCBANK BUY @ 1625 TGT 1680 SL 1590 SWING

# Format 5 — Multi-target
BUY SBIN CMP 798
TGT1 840 TGT2 860 TGT3 880
SL 775 | 1 WEEK
```

---

## 10. Extending the System

### Add Zerodha Kite API (live prices)
```python
# In price_fetcher.py, add:
from kiteconnect import KiteConnect
kite = KiteConnect(api_key="your_key")
kite.set_access_token("your_token")
quote = kite.quote(["NSE:RELIANCE"])
```

### Add Telegram Bot (auto-import)
```python
pip install python-telegram-bot
# Create bot, listen for messages in channel
# Call WhatsAppParser().parse_text(message) on each
# POST to /api/import/bulk-save
```

### Add email notifications
```python
import smtplib
# Trigger on alert fire in check_alerts()
```

---

## Support
For issues: check `import_log` table for import errors.
Price fetch failures: yfinance has rate limits — the 5-min cache prevents most issues.
