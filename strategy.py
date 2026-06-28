import yfinance as yf
import pandas as pd
import numpy as np
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ======================================================
# 1. Wilder RSI
# ======================================================

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ======================================================
# 2. 指標計算
# ======================================================

def prepare_indicators(df):
    df['SMA_20']  = df['Close'].rolling(20).mean()
    df['SMA_60']  = df['Close'].rolling(60).mean()
    df['SMA_100'] = df['Close'].rolling(100).mean()
    df['RSI']     = calculate_rsi(df['Close'])
    return df

# ======================================================
# 3. 趨勢策略
# ======================================================

def trend_strategy(df):
    today     = df.iloc[-1]
    yesterday = df.iloc[-2]

    strong_trend = (
        today['SMA_20'] > today['SMA_60'] > today['SMA_100']
    )
    golden_cross = (
        today['SMA_20'] > today['SMA_60'] and
        yesterday['SMA_20'] <= yesterday['SMA_60']
    )
    above_ma = (
        today['Close'] > today['SMA_20'] and
        today['Close'] > today['SMA_60']
    )

    if strong_trend and above_ma:
        return {
            'signal_type': 'TREND',
            'ma_status':   'bull',
            'reason':      '均線多頭排列' + ('＋黃金交叉' if golden_cross else ''),
            'rsi':         round(float(today['RSI']), 1),
            'price':       round(float(today['Close']), 2),
        }
    return None

# ======================================================
# 4. 反轉策略
# ======================================================

def reversal_strategy(df):
    today     = df.iloc[-1]
    yesterday = df.iloc[-2]

    rsi_rebound = (
        yesterday['RSI'] < 30 and
        today['RSI'] >= 30
    )
    bullish_candle = today['Close'] > today['Open']
    deep_pullback  = today['Close'] < today['SMA_60']

    if rsi_rebound and bullish_candle and deep_pullback:
        return {
            'signal_type': 'REVERSAL',
            'ma_status':   'bear',
            'reason':      'RSI 超賣反彈＋收紅K',
            'rsi':         round(float(today['RSI']), 1),
            'price':       round(float(today['Close']), 2),
        }
    return None

# ======================================================
# 5. 判斷均線排列（給分歧偵測用）
# ======================================================

def get_ma_status(df):
    today = df.iloc[-1]
    if today['SMA_20'] > today['SMA_60'] > today['SMA_100']:
        return 'bull'
    elif today['SMA_20'] < today['SMA_60'] < today['SMA_100']:
        return 'bear'
    else:
        return 'mixed'

# ======================================================
# 6. 綜合訊號：比對內部人方向
# ======================================================

def combine_signal(tech_signal, ma_status, insider_action, rsi, price):
    """
    insider_action: 'buy' or 'sell'
    tech_signal:    dict 或 None
    ma_status:      'bull' / 'bear' / 'mixed'
    """
    # 均線混亂 → 直接觀望
    if ma_status == 'mixed':
        return {
            'final':  'neutral',
            'label':  '觀望',
            'reason': '均線排列混亂，訊號不明確',
            'rsi':    rsi,
            'price':  price,
        }

    # 技術面與內部人一致
    if tech_signal:
        if ma_status == 'bull' and insider_action == 'buy':
            label  = '強烈買進' if rsi < 30 else '買進'
            final  = 'strong_buy' if rsi < 30 else 'buy'
            reason = f"技術面多頭＋內部人買進一致（{tech_signal['reason']}）"
        elif ma_status == 'bear' and insider_action == 'sell':
            label  = '強烈賣出' if rsi > 70 else '賣出'
            final  = 'strong_sell' if rsi > 70 else 'sell'
            reason = f"技術面空頭＋內部人賣出一致（{tech_signal['reason']}）"
        else:
            return {
                'final':  'neutral',
                'label':  '觀望',
                'reason': f"內部人{('買進' if insider_action == 'buy' else '賣出')}但技術面方向分歧，保守觀望",
                'rsi':    rsi,
                'price':  price,
            }
        return {
            'final':  final,
            'label':  label,
            'reason': reason,
            'rsi':    rsi,
            'price':  price,
        }

    # 沒有明確技術訊號，但均線方向明確
    if ma_status == 'bull' and insider_action == 'buy':
        return {
            'final':  'buy',
            'label':  '買進',
            'reason': '均線多頭排列，與內部人買進方向一致',
            'rsi':    rsi,
            'price':  price,
        }
    elif ma_status == 'bear' and insider_action == 'sell':
        return {
            'final':  'sell',
            'label':  '賣出',
            'reason': '均線空頭排列，與內部人賣出方向一致',
            'rsi':    rsi,
            'price':  price,
        }
    else:
        return {
            'final':  'neutral',
            'label':  '觀望',
            'reason': '技術面無明確訊號，保守觀望',
            'rsi':    rsi,
            'price':  price,
        }

# ======================================================
# 7. 分析單支股票
# ======================================================

def analyze_ticker(ticker, insider_action):
    """
    ticker:         股票代號（如 'AAPL'）
    insider_action: 'buy' or 'sell'
    回傳 dict 或 None
    """
    try:
        logging.info(f"[分析] {ticker} ...")
        df = yf.download(ticker, period='1y', interval='1d',
                         auto_adjust=True, progress=False)

        if df is None or len(df) < 110:
            logging.warning(f"{ticker} 資料不足，跳過")
            return None

        # 處理 MultiIndex（yfinance 新版會產生）
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = prepare_indicators(df)
        df = df.dropna(subset=['SMA_100', 'RSI'])

        if len(df) < 2:
            return None

        today     = df.iloc[-1]
        rsi       = round(float(today['RSI']), 1)
        price     = round(float(today['Close']), 2)
        ma_status = get_ma_status(df)

        trend_sig    = trend_strategy(df)
        reversal_sig = reversal_strategy(df)
        tech_signal  = trend_sig or reversal_sig

        result = combine_signal(tech_signal, ma_status, insider_action, rsi, price)
        result['ticker']          = ticker
        result['insider_action']  = insider_action
        result['ma_status']       = ma_status

        return result

    except Exception as e:
        logging.error(f"{ticker} 分析失敗: {e}")
        return None

# ======================================================
# 8. 批次分析（給 app.py 呼叫）
# ======================================================

def analyze_insider_trades(trades):
    seen = {}
    for t in trades:
        ticker = t.get('Ticker', '')
        trade_type = str(t.get('Trade Type', ''))
        if not ticker:
            continue
        action = 'buy' if trade_type.startswith('P') else 'sell'
        if ticker not in seen:
            seen[ticker] = action

    limited = list(seen.items())[:5]

    results = []
    for ticker, action in limited:
        result = analyze_ticker(ticker, action)
        if result:
            results.append(result)

    order = {'strong_buy': 0, 'buy': 1, 'neutral': 2, 'sell': 3, 'strong_sell': 4}
    results.sort(key=lambda x: order.get(x['final'], 99))

    return results
