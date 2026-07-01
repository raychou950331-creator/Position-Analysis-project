import os
import time
import pandas as pd
from io import StringIO
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 1. 載入環境變數
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def fetch_insider_data():
    """執行爬蟲並回傳清理過的 DataFrame"""
    with sync_playwright() as p:
        # 啟動瀏覽器 (建議設為 headless=False 方便你觀察)
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        url = "http://openinsider.com/latest-insider-sales"
        print(f"[INFO] Connecting to: {url}")
        
        try:
            # 前往網頁
            page.goto(url, wait_until="load", timeout=60000)
            
            # --- 修正廣告與彈窗干擾 ---
            print("[INFO] Cleaning page elements...")
            page.evaluate("""() => {
                const ads = document.querySelectorAll('.adsbygoogle, #google_ads_frame, .ad-unit');
                ads.forEach(ad => ad.remove());
            }""")
            
            # 滾動一下確保觸發渲染
            page.mouse.wheel(0, 500)
            time.sleep(3) 
            
            # --- 修正語法：獲取表格內容 ---
            print("[INFO] Waiting for data table to appear...")
            table_selector = "table.tinytable"
            page.wait_for_selector(table_selector, timeout=20000)
            
            # 使用 inner_html() 並手動補上 table 標籤，這是最穩定的做法
            inner_html = page.inner_html(table_selector)
            table_html = f"<table>{inner_html}</table>"
            
            print("[INFO] Parsing web data...")
            df_list = pd.read_html(StringIO(table_html))
            df = df_list[0]
            
            # --- 清理欄位名稱 ---
            # 移除空格與排序箭頭字元
            df.columns = [str(c).replace('▲', '').replace('▼', '').replace('\xa0', ' ').strip() for c in df.columns]
            
            browser.close()
            return df
            
        except Exception as e:
            print(f"[ERROR] Crawler encountered an error: {e}")
            if 'browser' in locals():
                browser.close()
            return None

def save_to_postgres(df):
    """將資料存入 PostgreSQL"""
    if df is None or df.empty:
        print("[WARNING] No data available to save.")
        return

    if not DATABASE_URL:
        print("[WARNING] Error: DATABASE_URL not found, please check your .env file.")
        return

    try:
        # Render 連線字串修正
        conn_url = DATABASE_URL
        if conn_url.startswith("postgres://"):
            conn_url = conn_url.replace("postgres://", "postgresql://", 1)

        engine = create_engine(conn_url)
        print("[INFO] Columns:", df.columns.tolist())

        print(f"[INFO] Writing to database...")
        # 寫入資料庫，表名設為 insider_trades
        df.to_sql('insider_trades', engine, if_exists='replace', index=False)
        print("[SUCCESS] Data successfully synchronized to Render PostgreSQL!")

    except Exception as e:
        print(f"[ERROR] Database write failed: {e}")

if __name__ == "__main__":
    raw_data = fetch_insider_data()
    
    if raw_data is not None:
        
        # 存檔
        save_to_postgres(raw_data)
    else:
        print("\n[ERROR] Process failed, please check network connection.")
