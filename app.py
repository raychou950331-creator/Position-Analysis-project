import os
import pandas as pd
from flask import Flask, render_template
from flask import request
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from flask import jsonify
from strategy import analyze_insider_trades
from flask import jsonify
import yfinance as yf
from datetime import datetime, timedelta
import time


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)

app = Flask(__name__)

engine = create_engine(DATABASE_URL)

_market_cache = {'data': None, 'timestamp': 0}
CACHE_TTL = 900

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
            last_updated = df['Filing Date'].iloc[0] if not df.empty else '未知'
            
    except Exception as e:
        print(f"[ERROR] Database read failed: {e}")
        df = pd.DataFrame()
        last_updated = '未知'

    return render_template("index.html", trades=df.to_dict(orient="records"), last_updated=last_updated)


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
    global _market_cache

    symbols_param = request.args.get('symbols', 'QQQ')

    if _market_cache['data'] and time.time() - _market_cache['timestamp'] < CACHE_TTL:
        cached = dict(_market_cache['data'])
        try:
            symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()][:4]
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
            cached['chart'] = chart_data
        except:
            pass
        return jsonify(cached)

    try:
        indices = {
            'S&P 500': '^GSPC',
            'Nasdaq': '^IXIC',
            '費城半導體': '^SOX',
            '羅素 2000': '^RUT'
        }

        index_data = []
        for name, symbol in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='2d')
                if len(hist) >= 2:
                    prev_close = float(hist['Close'].iloc[-2])
                    curr_close = float(hist['Close'].iloc[-1])
                    change_pct = (curr_close - prev_close) / prev_close * 100
                else:
                    curr_close = 0
                    change_pct = 0
                index_data.append({
                    'name': name,
                    'price': round(curr_close, 2),
                    'change_pct': round(change_pct, 2)
                })
            except:
                index_data.append({'name': name, 'price': 0, 'change_pct': 0})

        symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()][:4]
        chart_data = {}
        for symbol in symbols:
            try:
                hist = yf.Ticker(symbol).history(period='1mo', interval='1d')
                if hist.empty:
                    continue
                base = float(hist['Close'].iloc[0])
                chart_data[symbol] = {
                    'dates': [d.strftime('%m/%d') for d in hist.index],
                    'returns': [round((float(c) - base) / base * 100, 2) for c in hist['Close']]
                }
            except:
                pass

        result = {'indices': index_data, 'chart': chart_data}

        # 只快取大盤指數，走勢圖不快取
        _market_cache = {
            'data': {'indices': index_data, 'chart': chart_data},
            'timestamp': time.time()
        }

        return jsonify(result)

    except Exception as e:
        print(f"[ERROR] Market data failed: {e}")
        return jsonify({'indices': [], 'chart': {}})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
