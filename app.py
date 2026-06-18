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
        
        # 將 DataFrame 轉為帶有 Bootstrap 樣式的 HTML 表格
        table_html = df.to_html(classes='table table-striped table-hover', index=False)
        
        return render_template('index.html', table=table_html)
    except Exception as e:
        return f"資料庫讀取失敗：{e}"

if __name__ == "__main__":
    # 啟動本地伺服器
    app.run(debug=True)