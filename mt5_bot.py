from flask import Flask, jsonify, request
import MetaTrader5 as mt5
import numpy as np
import pandas as pd

app = Flask(__name__)

# Paramètres de la stratégie
SMA_FAST_PERIOD = 20
SMA_SLOW_PERIOD = 50
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9

def calculate_sma(series, period):
    return series.rolling(window=period).mean()

def calculate_macd(series, fast_period, slow_period, signal_period):
    ema_fast = series.ewm(span=fast_period, adjust=False).mean()
    ema_slow = series.ewm(span=slow_period, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    return macd_line, signal_line

def get_historical_prices(symbol, timeframe, limit):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, limit)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def analyze_market():
    symbol = "EURUSD"
    timeframe = mt5.TIMEFRAME_H1
    limit = 60

    prices_df = get_historical_prices(symbol, timeframe, limit)
    if prices_df is None or len(prices_df) < SMA_SLOW_PERIOD:
        return {'signal': 'wait'}

    close_prices = prices_df['close']

    sma_fast = calculate_sma(close_prices, SMA_FAST_PERIOD)
    sma_slow = calculate_sma(close_prices, SMA_SLOW_PERIOD)

    macd_line, signal_line = calculate_macd(close_prices, MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD)

    signal = 'wait'

    if sma_fast.iloc[-1] > sma_slow.iloc[-1] and sma_fast.iloc[-2] <= sma_slow.iloc[-2] and \
       macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:
        signal = 'buy'
    elif sma_fast.iloc[-1] < sma_slow.iloc[-1] and sma_fast.iloc[-2] >= sma_slow.iloc[-2] and \
         macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]:
        signal = 'sell'

    return {'signal': signal}

@app.route('/')
def index():
    return "Bienvenu sur le serveur Flask pour MT5"

@app.route('/get-balance', methods=['GET'])
def get_balance():
    if not mt5.initialize():
        return jsonify({"error": "Connexion MT5 échouée"})
    account = mt5.account_info()
    mt5.shutdown()
    if account is None:
        return jsonify({"error": "Impossible de récupérer les infos du compte"})
    return jsonify({
        "balance": account.balance,
        "equity": account.equity,
        "margin": account.margin,
        "free_margin": account.margin_free
    })

@app.route('/analyze-market', methods=['GET'])
def get_analysis(): # Vérifiez si le nom de votre fonction est le même
    if not mt5.initialize():
        return jsonify({'error': 'MT5 not initialized'}), 500
    analysis = analyze_market()
    mt5.shutdown()
    return jsonify(analysis)

@app.route('/trade', methods=['GET'])
def trade():
    trade_type = request.args.get('type')
    stop_loss_pips = request.args.get('stop_loss', default=20, type=int)
    take_profit_pips = request.args.get('take_profit', default=40, type=int)

    if not mt5.initialize():
        return jsonify({'error': 'MT5 not initialized'}), 500
    symbol = "EURUSD"
    lot = 0.1
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        mt5.shutdown()
        return jsonify({'error': 'Symbol not found'}), 500
    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)
    point = mt5.symbol_info(symbol).point
    price = mt5.symbol_info_tick(symbol).ask if trade_type == 'buy' else mt5.symbol_info_tick(symbol).bid
    sl = price - stop_loss_pips * point if trade_type == 'buy' else price + stop_loss_pips * point
    tp = price + take_profit_pips * point if trade_type == 'buy' else price - take_profit_pips * point
    request_data = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if trade_type == 'buy' else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 123456,
        "comment": "PHP Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request_data)
    mt5.shutdown()
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return jsonify({'error': 'Trade failed', 'details': result._asdict()}), 500
    return jsonify({'status': 'success', 'result': result._asdict()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)