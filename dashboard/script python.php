import MetaTrader5 as mt5
import requests
import time

MT5_SYMBOL = "EURUSD"
USER_ID = 1

if not mt5.initialize():
    print("Erreur MT5")
    quit()

while True:
    tick = mt5.symbol_info_tick(MT5_SYMBOL)
    price = tick.ask

    print(f"Prix actuel : {price}")

    # 1. Envoi signal au serveur PHP
    res = requests.post("http://localhost/trading-bot/api/get_signal.php", data={
        "price": price,
        "user_id": USER_ID
    })
    signal = res.json().get("signal")

    print("Signal reçu :", signal)

    # 2. Envoi action
    requests.post("http://localhost/trading-bot/api/trade_action.php", data={
        "user_id": USER_ID,
        "price": price,
        "signal": signal,
        "amount": 1.00
    })

    time.sleep(10)  # boucle toutes les 10 secondes
