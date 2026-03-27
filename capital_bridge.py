import time, json
from pathlib import Path
from binance.client import Client
from bot.risk_manager import calcular_valor_trade

from bot.config import SECRETS

client = Client(SECRETS["binance_api_key"], SECRETS["binance_api_secret"])

OUT = Path("/tmp/capital_state.json")

def get_balance():
    acc = client.get_account()
    for b in acc["balances"]:
        if b["asset"] == "USDT":
            return float(b["free"])
    return 0.0

while True:
    try:
        saldo = get_balance()
        valor = calcular_valor_trade(saldo)

        data = {
            "saldo_usdt": saldo,
            "valor_trade": valor
        }

        OUT.write_text(json.dumps(data, indent=2))
        print("💰 saldo:", saldo, "valor trade:", valor)

    except Exception as e:
        print("erro:", e)

    time.sleep(10)
