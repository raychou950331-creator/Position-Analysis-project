import os
import pandas as pd
from flask import Flask, render_template
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from flask import jsonify
from strategy import analyze_insider_trades
from flask import jsonify
import yfinance as yf
from datetime import datetime, timedelta

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)

app = Flask(__name__)

engine = create_engine(DATABASE_URL)


@app.route("/")
def index():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    "Filing Date",
                    "Trade Date",
                    "Ticker",
                    "Company Name",
                    "Insider Name",
                    "Title",
                    "Trade Type",
                    "Price",
                    "Qty",
                    "Value"
                FROM insider_trades
                ORDER BY "Filing Date" DESC
                LIMIT 50
            """))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        print(f"[ERROR] Database read failed: {e}")
        df = pd.DataFrame()

    return render_template("index.html", trades=df.to_dict(orient="records"))


@app.route("/api/signals")
def get_signals():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT "Ticker", "Trade Type"
                FROM insider_trades
                ORDER BY "Filing Date" DESC
                LIMIT 100
            """))
            trades = [dict(row._mapping) for row in result]
        signals = analyze_insider_trades(trades)
        return jsonify(signals)
    except Exception as e:
        print(f"[ERROR] Signals failed: {e}")
        return jsonify([])
        
@app.route("/analytics")
def analytics():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT "Ticker", "Trade Type"
                FROM insider_trades
                ORDER BY "Filing Date" DESC
                LIMIT 100
            """))
            trades = [dict(row._mapping) for row in result]
        signals = analyze_insider_trades(trades)
    except Exception as e:
        print(f"[ERROR] Analytics failed: {e}")
        signals = []
    return render_template("analytics.html", signals=signals)
    
@app.route("/market-data")
def market_data():
    return render_template("market_data.html")

@app.route("/api/market-data")
def get_market_data():
    try:
        # 大盤指數
        indices = {
            'S&P 500': '^GSPC',
            'Nasdaq': '^IXIC',
            '費城半導體': '^SOX',
            '羅素 2000': '^RUT'
        }

        index_data = []
        for name, symbol in indices.items():
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period='2d')
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                curr_close = hist['Close'].iloc[-1]
                change_pct = ((curr_close - prev_close) / prev_close) * 100
            else:
                curr_close = info.get('regularMarketPrice', 0)
                change_pct = info.get('regularMarketChangePercent', 0)

            index_data.append({
                'name': name,
                'price': round(float(curr_close), 2),
                'change_pct': round(float(change_pct), 2)
            })

        # 走勢圖資料（預設 QQQ + 可自訂）
        symbols = request.args.get('symbols', 'QQQ').split(',')
        symbols = [s.strip().upper() for s in symbols if s.strip()][:4]

        chart_data = {}
        for symbol in symbols:
            hist = yf.Ticker(symbol).history(period='1mo', interval='1d')
            if hist.empty:
                continue
            base = float(hist['Close'].iloc[0])
            chart_data[symbol] = {
                'dates': [d.strftime('%m/%d') for d in hist.index],
                'returns': [round((float(c) - base) / base * 100, 2) for c in hist['Close']]
            }

        return jsonify({'indices': index_data, 'chart': chart_data})

    except Exception as e:
        print(f"[ERROR] Market data failed: {e}")
        return jsonify({'indices': [], 'chart': {}})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
