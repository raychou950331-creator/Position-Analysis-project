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
        
        # 【💡 重點優化】：確保欄位名稱存在，並只篩選出你需要的 4 個核心維度
        # 這裡會自動對應你的爬蟲欄位名稱，如果爬蟲存的欄位叫 'name' 或 'owner'，請根據真實狀況微調
        available_cols = df.columns.tolist()
        
        # 尋找人名/組織可能對應的欄位名稱
        insider_col = 'insider'
        for col in ['insider', 'name', 'owner', 'insider_name']:
            if col in available_cols:
                insider_col = col
                break
                
        # 篩選並統一重新命名欄位，餵給前端
        df_clean = pd.DataFrame()
        df_clean['ticker'] = df['ticker'] if 'ticker' in df.columns else df.iloc[:, 0]
        df_clean['insider'] = df[insider_col] if insider_col in df.columns else "Unknown Entity"
        df_clean['transaction'] = df['transaction'] if 'transaction' in df.columns else "Transaction"
        df_clean['value'] = df['value'] if 'value' in df.columns else "0"
        
        # 將 DataFrame 轉換為字典格式的 List，完美對齊 index.html 的迴圈
        data_list = df_clean.to_dict(orient='records')
        
        # 成功將對齊好的 data_list 傳給前端
        return render_template('index.html', data_list=data_list)
        
    except Exception as e:
        return f"資料庫讀取失敗：{e}"

if __name__ == "__main__":
    # 啟動本地伺服器
    app.run(debug=True)
