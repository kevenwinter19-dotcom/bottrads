import time, requests, json

URL = "http://127.0.0.1:8080/api/estado"

print("🔫 SNIPER EXTERNO ATIVO")

def sniper_filter(sinal):
    score = sinal.get("score", 0)
    direcao = sinal.get("direcao", "")
    flow = sinal.get("flow_proxy", {})
    whale = sinal.get("whale_real", {})
    
    delta = flow.get("delta_ratio", 0)

    # filtros sniper
    if abs(score) < 5:
        return False, "score fraco"
    if abs(delta) < 0.15:
        return False, "fluxo fraco"
    if whale.get("label") == "WHALE_NEUTRO":
        return False, "sem whale"

    return True, "entrada válida"


while True:
    try:
        r = requests.get(URL, timeout=3)
        data = r.json()

        sinais = data.get("ultimo_sinal", {})

        for par, sinal in sinais.items():
            ok, motivo = sniper_filter(sinal)

            if not ok:
                print(f"❌ BLOQUEADO {par} → {motivo}")
            else:
                print(f"✅ LIBERADO {par}")

    except Exception as e:
        print("erro:", e)

    time.sleep(5)
