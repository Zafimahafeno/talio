from flask import Flask, jsonify, request, render_template
import requests
import time
import threading

app = Flask(__name__)

# Configuration
LOCAL_API_URL = 'http://127.0.0.1:5002'  # IMPORTANT: Mettre à jour avec l'IP de ta machine locale!
TRADE_INTERVAL = 15  # Vérifier le signal toutes les 15 secondes
SYMBOL = "EURUSD" # Add this line
LOT = 0.02 # Add this line

# Variables globales
mt5_initialized_remote = False
auto_trade_thread = None  # Pour stocker le thread, si nécessaire
position_ouverte = False
type_position = None

# Fonctions pour communiquer avec l'API locale
def init_mt5_local(login, password, server):
    try:
        response = requests.post(f'{LOCAL_API_URL}/init-mt5', json={'login': login, 'password': password, 'server': server})
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to connect to local API: {e}'}, 500

def get_balance_local():
    try:
        response = requests.get(f'{LOCAL_API_URL}/get-local-balance')
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to get balance from local API: {e}'}, 500

def get_prices_local(symbol):
    try:
        response = requests.get(f'{LOCAL_API_URL}/get-local-prices/{symbol}')
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to get prices from local API: {e}'}, 500

def execute_trade_local(trade_type, symbol, lot, price):
    try:
        response = requests.get(
            f'{LOCAL_API_URL}/execute-local-trade/{trade_type}/{symbol}/{lot}/{price}')
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to execute trade via local API: {e}'}, 500

# Fonction d'analyse du marché (adaptée pour utiliser l'API locale pour récupérer les prix)
def analyze_market():
    # Ici, on récupère les prix via l'API locale
    prices_response = get_prices_local(SYMBOL) # Assumes SYMBOL is defined
    if prices_response[1] != 200: # Check the status code.
        return {'signal': 'wait'}
    prices_data = prices_response[0]
    if not prices_data:
        return {'signal': 'wait'}
    # Générer un signal aléatoire pour le test (À REMPLACER par ta logique finale)
    import random
    if random.random() < 0.5:
        signal = 'buy'
    else:
        signal = 'sell'
    print(f"Signal (Alwaysdata): {signal}")
    return {'signal': signal}

# Fonction principale pour l'exécution automatique (adaptée pour utiliser l'API locale)
def auto_trading_loop():
    global position_ouverte, type_position
    try:
        while True:
            if not position_ouverte:
                analysis = analyze_market()
                signal = analysis.get('signal')
                if signal == 'buy':
                    print("Signal d'achat détecté. Tentative d'exécution via local API...")
                    prices_response = get_prices_local(SYMBOL)
                    if prices_response[1] == 200:
                        prices = prices_response[0]
                        execute_trade_local('buy', SYMBOL, LOT, prices['ask'])
                        position_ouverte = True
                        type_position = 'buy'
                    else:
                        print("Failed to get price to execute")
                elif signal == 'sell':
                    print("Signal de vente détecté. Tentative d'exécution via local API...")
                    prices_response = get_prices_local(SYMBOL)
                    if prices_response[1] == 200:
                        prices = prices_response[0]
                        execute_trade_local('sell', SYMBOL, LOT, prices['bid'])
                        position_ouverte = True
                        type_position = 'sell'
                    else:
                        print("Failed to get price to execute")
                else:
                    print("Pas de signal de trading.")
            else:
                print(f"Position {type_position} ouverte (Alwaysdata).")
                #  Ajouter ici la logique pour vérifier si la position est toujours ouverte.
                #  Cela pourrait nécessiter un endpoint supplémentaire sur l'API locale pour récupérer
                #  les informations sur les positions ouvertes, ou une logique pour suivre les ordres passés.
                #  Pour simplifier, on suppose ici que la position peut être fermée par SL/TP à tout moment.
                time.sleep(TRADE_INTERVAL)
    except KeyboardInterrupt:
        print("Boucle d'exécution automatique interrompue.")

@app.route('/')
def index():
    return render_template('login.html')  # Tu devras créer un template login.html

@app.route('/init-mt5', methods=['POST'])
def init_mt5_remote():
    global mt5_initialized_remote, auto_trade_thread
    login = request.json.get('login')
    password = request.json.get('password')
    server = request.json.get('server')

    if not login or not password or not server:
        return jsonify({'error': 'Missing login, password, or server'}), 400

    result, status_code = init_mt5_local(login, password, server)
    if status_code == 200:
        mt5_initialized_remote = True
        # Démarrer le thread de trading automatique sur Alwaysdata
        auto_trade_thread = threading.Thread(target=auto_trading_loop)
        auto_trade_thread.daemon = True
        auto_trade_thread.start()
        return jsonify(result), status_code
    else:
        return jsonify(result), status_code

@app.route('/get-balance', methods=['GET'])
def get_balance_route_remote():
    if not mt5_initialized_remote:
        return jsonify({'error': 'MT5 not initialized (via local API). Call /init-mt5 first.'}), 400
    balance_data, status_code = get_balance_local()
    return jsonify(balance_data), status_code
@app.route('/analyze-market', methods=['GET'])
def get_analysis_route_remote():
    analysis = analyze_market()
    return jsonify(analysis)

@app.route('/trade', methods=['GET'])
def trade_route_remote():
    global position_ouverte
    if not mt5_initialized_remote:
        return jsonify({'error': 'MT5 not initialized (via local API). Call /init-mt5 first.'}), 400
    trade_type = request.args.get('type')
    if not trade_type:
        return jsonify({'error': 'Missing trade type (buy or sell)'}), 400
    if trade_type.lower() not in ['buy', 'sell']:
        return jsonify({'error': 'Invalid trade type'}), 400
    if position_ouverte:
        return jsonify({'error': 'A position is already open'}), 400
    # L'exécution réelle se fait dans auto_trading_loop qui appelle execute_trade_local
    # Ici, on signale juste que la tentative va être faite
    return jsonify({'status': f'Attempting to {trade_type} via local API (check local server logs)'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
