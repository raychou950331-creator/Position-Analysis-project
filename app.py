import os
import pandas as pd
from flask import Flask, render_template
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

@app.route('/')
def index():
    try:
        engine = create_engine(DATABASE_URL)
        query = "SELECT * FROM insider_trades LIMIT 30"
        df = pd.read_sql(query, engine)
        
        # 建立 8 欄位的精簡資料集
        df_clean = pd.DataFrame()
        
        # 1. Trade Date
        df_clean['trade_date'] = df['Trade Date'].astype(str) if 'Trade Date' in df.columns else (df['Trade_Date'].astype(str) if 'Trade_Date' in df.columns else "N/A")
        
        # 2. Ticker
        df_clean['ticker'] = df['Ticker'].astype(str).str.upper() if 'Ticker' in df.columns else "N/A"
        
        # 3. Insider Name
        df_clean['insider'] = df['Insider Name'].astype(str) if 'Insider Name' in df.columns else (df['Insider_Name'].astype(str) if 'Insider_Name' in df.columns else "N/A")
        
        # 4. Trade Type (買或賣)
        df_clean['transaction'] = df['Trade Type'].astype(str) if 'Trade Type' in df.columns else (df['Trade_Type'].astype(str) if 'Trade_Type' in df.columns else "N/A")
        
        # 5. Price
        df_clean['price'] = df['Price'].astype(str) if 'Price' in df.columns else "$0"
        
        # 6. Qty
        df_clean['qty'] = df['Qty'].astype(str) if 'Qty' in df.columns else "0"
        
        # 7. ΔOwn
        df_clean['delta_own'] = df['ΔOwn'].astype(str) if 'ΔOwn' in df.columns else "0%"
        
        # 8. Value
        df_clean['value'] = df['Value'].astype(str) if 'Value' in df.columns else "$0"

        data_list = df_clean.to_dict(orient='records')
        return render_template('index.html', data_list=data_list)
        
    except Exception as e:
        return f"資料庫讀取失敗：{e}"

if __name__ == "__main__":
    app.run(debug=True)
