import os
import pandas as pd
from flask import Flask, render_template
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

app = Flask(__name__)

# 資料庫連線設定
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

@app.route('/')
def index():
    try:
        # 建立資料庫連線引擎
        engine = create_engine(DATABASE_URL)
        
        # 從資料庫抓取最新 30 筆交易資料
        query = "SELECT * FROM insider_trades LIMIT 30"
        df = pd.read_sql(query, engine)
        
        # 建立一個乾淨、精簡的新 DataFrame 餵給前端
        df_clean = pd.DataFrame()
        
        # 1. 股票代號 (OpenInsider 原始欄位名為 'Ticker')
        if 'Ticker' in df.columns:
            df_clean['ticker'] = df['Ticker'].astype(str).str.upper()
        else:
            df_clean['ticker'] = df.iloc[:, 3].astype(str).str.upper() # 保底取第四欄
            
        # 2. 人名或組織或企業 (OpenInsider 原始欄位名為 'Insider Name')
        if 'Insider Name' in df.columns:
            df_clean['insider'] = df['Insider Name'].astype(str)
        elif 'Insider_Name' in df.columns:
            df_clean['insider'] = df['Insider_Name'].astype(str)
        else:
            df_clean['insider'] = "Unknown Entity"

        # 3. 買或賣 (OpenInsider 原始欄位名為 'Trade Type')
        if 'Trade Type' in df.columns:
            df_clean['transaction'] = df['Trade Type'].astype(str)
        elif 'Trade_Type' in df.columns:
            df_clean['transaction'] = df['Trade_Type'].astype(str)
        else:
            df_clean['transaction'] = "Transaction"

        # 4. 金額 (OpenInsider 原始欄位名為 'Value')
        if 'Value' in df.columns:
            df_clean['value'] = df['Value'].astype(str)
        else:
            df_clean['value'] = "$0"

        # 轉成前端需要的字典格式
        data_list = df_clean.to_dict(orient='records')
        
        return render_template('index.html', data_list=data_list)
        
    except Exception as e:
        return f"資料庫讀取失敗，請確認爬蟲是否成功寫入：{e}"

if __name__ == "__main__":
    app.run(debug=True)
