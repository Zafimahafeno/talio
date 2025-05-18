from flask import Flask, jsonify, request, render_template
import MetaTrader5 as mt5
import pandas as pd
import time
import threading

app = Flask(__name__)

# Paramètres de la stratégie
SMA_FAST_PERIOD = 20
SMA_SLOW_PERIOD = 50
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9
# Paramètres de trading
SYMBOL = "EURUSD"
LOT = 0.02
STOP_LOSS_PIPS = 50
TAKE_PROFIT_PIPS = 150
MAGIC_NUMBER = 123456
DEVIATION = 20
TRADE_INTERVAL = 15  # Vérifier le signal toutes les 15 secondes (pour des tests plus rapides)
# Variables globales
position_ouverte = False
type_position = None
mt5_initialized = False  # Nouveau: Pour suivre l'état d'initialisation de MT5
# Lock pour protéger l'accès à MT5
mt5_lock = threading.Lock()
# Fonctions de calcul d'indicateurs (inchangées)
def calculate_sma(series, period):
    return series.rolling(window=period).mean()
def calculate_macd(series, fast_period, slow_period, signal_period):
    ema_fast = series.ewm(span=fast_period, adjust=False).mean()
    ema_slow = series.ewm(span=slow_period, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    return macd_line, signal_line
# Fonction pour récupérer les prix historiques (inchangée)
def get_historical_prices(symbol, timeframe, limit):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, limit)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df
# Fonction d'analyse du marché (AUCUNE condition de signal basée sur les SMA)
def analyze_market():
    timeframe = mt5.TIMEFRAME_H1  # Analyse sur une période plus courte pour des tests
    limit = 2  # Récupérer seulement les deux dernières bougies pour la vérification

    prices_df = get_historical_prices(SYMBOL, timeframe, limit)
    if prices_df is None or len(prices_df) < 1:
        return {'signal': 'wait'}
    # Générer un signal aléatoire pour le test (À REMPLACER par ta logique finale)
    import random
    if random.random() < 0.5:
        signal = 'buy'
    else:
        signal = 'sell'
    print(f"Signal (aléatoire pour le test) : {signal}")
    return {'signal': signal}
# Fonction pour vérifier si une position est ouverte
def check_open_position():
    with mt5_lock:  # Utiliser le lock
        positions = mt5.positions_get(symbol=SYMBOL)
        if positions:
            return True, positions[0].type
        return False, None
# Fonction pour fermer une position ouverte
def close_position(ticket):
    with mt5_lock:
        position = mt5.positions_get(ticket=ticket)
        if position:
            symbol = position[0].symbol
            volume = position[0].volume
            type = mt5.ORDER_TYPE_SELL if position[0].type == 0 else mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).bid if type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": type,
                "price": price,
                "deviation": DEVIATION,
                "magic": MAGIC_NUMBER,
                "comment": "Close Auto",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
                "position": ticket,
            }
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(
                    f"Erreur lors de la fermeture de la position {ticket}, retcode={result.retcode}")
                print(f"Erreur: {result.comment}")
                return False
            else:
                print(f"Position {ticket} fermée avec succès")
                return True
        return False
# Fonction pour passer un ordre de trading (modifiée pour vérifier les positions existantes)
def execute_trade(trade_type):
    global position_ouverte, type_position
    is_open, open_type = check_open_position()
    if is_open:
        print(
            f"Une position { 'BUY' if open_type == 0 else 'SELL'} est déjà ouverte. Aucune nouvelle ordre ne sera placé.")
        return False
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        print(f"Erreur: Impossible de récupérer les informations pour {SYMBOL}")
        return False
    if not symbol_info.visible:
        if not mt5.symbol_select(SYMBOL, True):
            print(f"Erreur: Impossible de sélectionner le symbole {SYMBOL}")
            return False
    point = mt5.symbol_info(SYMBOL).point
    price = mt5.symbol_info_tick(
        SYMBOL).ask if trade_type == 'buy' else mt5.symbol_info_tick(SYMBOL).bid
    sl = price - STOP_LOSS_PIPS * \
        point if trade_type == 'buy' else price + STOP_LOSS_PIPS * point
    tp = price + TAKE_PROFIT_PIPS * \
        point if trade_type == 'buy' else price - TAKE_PROFIT_PIPS * point
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT,
        "type": mt5.ORDER_TYPE_BUY if trade_type == 'buy' else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": DEVIATION,
        "magic": MAGIC_NUMBER,
        "comment": "Auto Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    with mt5_lock:  # Utiliser le lock
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Échec de l'ordre {trade_type}, retcode={result.retcode}")
            print(f"Erreur: {result.comment}")
            return False
        else:
            print(
                f"Ordre {trade_type} exécuté avec succès, order_id={result.order}")
            position_ouverte = True
            type_position = trade_type
            return True
# Fonction principale pour l'exécution automatique (modifiée pour la gestion des positions)
def auto_trading_loop():
    global position_ouverte, type_position
    # Plus besoin d'initialiser MT5 ici
    try:
        while True:
            is_open, open_type = check_open_position()
            if not is_open:
                analysis = analyze_market()
                signal = analysis.get('signal')
                if signal == 'buy':
                    print("Signal d'achat détecté. Tentative d'exécution...")
                    execute_trade('buy')
                elif signal == 'sell':
                    print("Signal de vente détecté. Tentative d'exécution...")
                    execute_trade('sell')
                else:
                    print("Pas de signal de trading.")
            else:
                # Logique pour vérifier si une position a été fermée par SL/TP
                with mt5_lock:  # Utiliser le lock
                    current_positions = mt5.positions_get(symbol=SYMBOL)
                if not current_positions:
                    print(
                        "Position fermée (SL/TP ou manuellement). Préparation pour un nouvel ordre.")
                    position_ouverte = False
                    type_position = None
                else:
                    print(
                        f"Position { 'BUY' if open_type == 0 else 'SELL'} toujours ouverte.")
            time.sleep(TRADE_INTERVAL)
    except KeyboardInterrupt:
        print("Boucle d'exécution automatique interrompue.")
    finally:
        with mt5_lock:
            mt5.shutdown()
@app.route('/')
def index():
    return render_template('login.html')
@app.route('/init-mt5', methods=['POST'])
def init_mt5():
    global mt5_initialized, auto_trade_thread
    if mt5_initialized:
        return jsonify({'error': 'MT5 already initialized'}), 400
    
    login = request.json.get('login')
    password = request.json.get('password')
    server = request.json.get('server')
    
    if not login or not password or not server:
        return jsonify({'error': 'Missing login, password, or server'}), 400
    
    # Convertir explicitement le login en entier
    try:
        login = int(login)
    except ValueError:
        return jsonify({'error': 'Login must be a valid number'}), 400
    
    # Initialiser MT5 avec les informations fournies
    if not mt5.initialize(login=login, password=password, server=server):
        error_message = mt5.last_error()
        return jsonify({"error": f"Connexion MT5 échouée: {error_message}"}), 500
    
    mt5_initialized = True  # Marquer comme initialisé
    
    # Démarrer le thread de trading automatique
    auto_trade_thread = threading.Thread(target=auto_trading_loop)
    auto_trade_thread.daemon = True
    auto_trade_thread.start()
    
    return jsonify({'status': 'MT5 initialized and auto trading started'}), 200
@app.route('/get-balance', methods=['GET'])
def get_balance_route():
    if not mt5_initialized:
        return jsonify({'error': 'MT5 not initialized. Call /init-mt5 first.'}), 400
    with mt5_lock:  # Utiliser le lock
        account = mt5.account_info()
    if account is None:
        return jsonify({"error": "Impossible de récupérer les infos du compte"})
    return jsonify({
        "balance": account.balance,
        "equity": account.equity,
        "margin": account.margin,
        "free_margin": account.margin_free
    })
@app.route('/analyze-market', methods=['GET'])
def get_analysis_route():
    if not mt5_initialized:
        return jsonify({'error': 'MT5 not initialized. Call /init-mt5 first.'}), 400
    analysis = analyze_market()
    return jsonify(analysis)
@app.route('/trade', methods=['GET'])
def trade_route():
    if not mt5_initialized:
        return jsonify({'error': 'MT5 not initialized. Call /init-mt5 first.'}), 400
    trade_type = request.args.get('type')
    stop_loss_pips = request.args.get('stop_loss', default=STOP_LOSS_PIPS, type=int)
    take_profit_pips = request.args.get(
        'take_profit', default=TAKE_PROFIT_PIPS, type=int)
    if not trade_type:
        return jsonify({'error': 'Missing trade type (buy or sell)'}), 400
    symbol = SYMBOL
    lot = LOT
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return jsonify({'error': 'Symbol not found'}), 500
    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)
    point = mt5.symbol_info(symbol).point
    price = mt5.symbol_info_tick(
        symbol).ask if trade_type == 'buy' else mt5.symbol_info_tick(symbol).bid
    sl = price - stop_loss_pips * \
        point if trade_type == 'buy' else price + stop_loss_pips * point
    tp = price + take_profit_pips * \
        point if trade_type == 'buy' else price - take_profit_pips * point
    request_data = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if trade_type == 'buy' else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "PHP Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    with mt5_lock:  # Utiliser le lock
        result = mt5.order_send(request_data)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return jsonify({'error': 'Trade failed', 'details': result._asdict()}), 500
    return jsonify({'status': 'success', 'result': result._asdict()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True,
            use_reloader=False)  # Lancer Flask seulement

