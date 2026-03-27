import time
import json
from pathlib import Path

OUT = Path("/tmp/fund_state.json")
CAPITAL = Path("/tmp/capital_state.json")

VALOR_FIXO_TESTE = 10.0

def get_saldo():
    try:
        if CAPITAL.exists():
            data = json.loads(CAPITAL.read_text(encoding="utf-8"))
            return float(data.get("saldo_usdt", 0))
    except Exception:
        pass
    return 0.0

def salvar(data):
    OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")

while True:
    try:
        saldo = get_saldo()
        data = {
            "saldo": round(saldo, 2),
            "valor_trade": VALOR_FIXO_TESTE,
            "risk_percent": 0.0,
            "win_streak": 0,
            "loss_streak": 0,
            "modo": "teste_fixo_10_usdt"
        }
        salvar(data)
    except Exception as e:
        salvar({"erro": str(e)})

    time.sleep(10)
