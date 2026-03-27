import json
import time
import hashlib
import urllib.request
from pathlib import Path

from bot.ai_decider import OpenAIDecisionEngine

URL = "http://127.0.0.1:8080/api/estado"
OUT = Path("/tmp/ai_bridge_state.json")
CACHE = Path("/tmp/ai_bridge_cache.json")

engine = OpenAIDecisionEngine()

CALL_INTERVAL_OK = 300
CALL_INTERVAL_IDLE = 20
COOLDOWN_429 = 1800

def fetch_state():
    with urllib.request.urlopen(URL, timeout=5) as r:
        return json.load(r)

def load_cache():
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "last_hash": "",
        "last_pair": "",
        "last_decision": {},
        "cooldown_until": 0,
        "last_call_ts": 0,
    }

def save_cache(cache):
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

def save_out(payload):
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def signal_strength(sinal):
    score = float(sinal.get("score", 0) or 0)
    flow = sinal.get("flow_proxy") or {}
    whale = sinal.get("whale_real") or {}
    delta = abs(float(flow.get("delta_ratio", 0) or 0))
    whale_score = abs(float(whale.get("score", 0) or 0))
    return abs(score) + (delta * 10.0) + (whale_score * 5.0)

def build_ctx(pair, sinal, estado):
    return {
        "pair": pair,
        "technical": {
            "score": sinal.get("score", 0),
            "direcao": sinal.get("direcao", ""),
            "motivo": sinal.get("motivo", ""),
            "timeframes": sinal.get("timeframes", {}),
        },
        "flow_proxy": sinal.get("flow_proxy", {}),
        "whale_real": sinal.get("whale_real", {}),
        "news": estado.get("news_summary", {}) if isinstance(estado.get("news_summary", {}), dict) else {},
        "risk": sinal.get("risk_plan", {}),
    }

def ctx_hash(ctx):
    raw = json.dumps(ctx, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def main():
    while True:
        try:
            estado = fetch_state()
            ultimo = estado.get("ultimo_sinal") or {}
            cache = load_cache()
            now = int(time.time())

            out = {
                "ai_last_decision": cache.get("last_decision", {}),
                "pairs": {},
                "debug": {}
            }

            if not ultimo:
                out["debug"] = {"reason": "sem_ultimo_sinal"}
                save_out(out)
                save_cache(cache)
                time.sleep(CALL_INTERVAL_IDLE)
                continue

            items = [(pair, sinal) for pair, sinal in ultimo.items() if isinstance(sinal, dict)]
            items.sort(key=lambda x: signal_strength(x[1]), reverse=True)

            pair, sinal = items[0]
            ctx = build_ctx(pair, sinal, estado)
            h = ctx_hash(ctx)

            out["debug"] = {
                "selected_pair": pair,
                "score": sinal.get("score", 0),
                "direcao": sinal.get("direcao", ""),
            }

            if (
                cache.get("last_hash") == h and
                cache.get("last_pair") == pair and
                (now - int(cache.get("last_call_ts", 0))) < CALL_INTERVAL_OK
            ):
                out["ai_last_decision"] = cache.get("last_decision", {})
                out["pairs"][pair] = cache.get("last_decision", {})
                out["debug"]["reason"] = "cache_reuse"
                save_out(out)
                save_cache(cache)
                time.sleep(CALL_INTERVAL_IDLE)
                continue

            if now < int(cache.get("cooldown_until", 0)):
                decision = {
                    "acao": "AGUARDAR",
                    "confianca": 0.0,
                    "estrategia": "cooldown_openai",
                    "motivo": "OpenAI em cooldown por quota/rate limit",
                    "provider": "cooldown",
                    "model": "none",
                }
                out["ai_last_decision"] = decision
                out["pairs"][pair] = decision
                out["debug"]["reason"] = "cooldown"
                save_out(out)
                save_cache(cache)
                time.sleep(CALL_INTERVAL_IDLE)
                continue

            try:
                decision = engine.decidir(ctx)
            except Exception as e:
                msg = str(e).lower()
                if "429" in msg or "insufficient_quota" in msg or "quota" in msg or "rate limit" in msg:
                    cache["cooldown_until"] = now + COOLDOWN_429
                    decision = {
                        "acao": "AGUARDAR",
                        "confianca": 0.0,
                        "estrategia": "cooldown_openai",
                        "motivo": "OpenAI em cooldown por quota/rate limit",
                        "provider": "cooldown",
                        "model": "none",
                    }
                else:
                    decision = {
                        "acao": "AGUARDAR",
                        "confianca": 0.0,
                        "estrategia": "erro_openai",
                        "motivo": str(e)[:180],
                        "provider": "error",
                        "model": "none",
                    }

            cache["last_hash"] = h
            cache["last_pair"] = pair
            cache["last_decision"] = decision
            cache["last_call_ts"] = now
            save_cache(cache)

            out["ai_last_decision"] = decision
            out["pairs"][pair] = decision
            out["debug"]["reason"] = "fresh_call"
            save_out(out)

        except Exception as e:
            save_out({
                "ai_last_decision": {
                    "acao": "AGUARDAR",
                    "confianca": 0.0,
                    "estrategia": "bridge_error",
                    "motivo": str(e)[:180],
                    "provider": "bridge",
                    "model": "none",
                },
                "pairs": {},
                "debug": {"reason": "exception", "error": str(e)[:200]}
            })

        time.sleep(CALL_INTERVAL_IDLE)

if __name__ == "__main__":
    main()
