import os
import pandas as pd
from flask import Flask, render_template
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
