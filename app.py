import os
import pandas as pd
from flask import Flask, render_template
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from flask import jsonify
from strategy import analyze_insider_trades

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
