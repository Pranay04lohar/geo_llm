import json
import sys
import requests

try:
    from app.services.core_llm_agent.config import get_openrouter_config
except Exception as e:
    print(f"Failed to import config: {e}")
    sys.exit(1)


def main() -> int:
    cfg = get_openrouter_config()
    api_key = cfg.get("api_key", "")

    if not api_key:
        print("OPENROUTER_API_KEY missing (not found in environment/.env)")
        return 2

    base = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": cfg.get("referrer") or "http://localhost",
        "X-Title": cfg.get("app_title") or "GeoLLM Agent",
    }

    payload = {
        "model": cfg.get("intent_model"),
        "messages": [
            {"role": "system", "content": "You are a tester. Respond with a compact JSON object."},
            {"role": "user", "content": "Reply with {\"status\":\"ok\"} only."},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    print("Using model:", payload["model"]) 
    print("Headers set: HTTP-Referer=", headers["HTTP-Referer"], ", X-Title=", headers["X-Title"], sep="")

    try:
        r = requests.post(base, headers=headers, data=json.dumps(payload), timeout=25)
        print("Status:", r.status_code)
        txt = r.text
        print("Body (first 800 chars):\n", txt[:800])
        return 0 if r.ok else 1
    except Exception as e:
        print("Error:", e)
        return 3


if __name__ == "__main__":
    sys.exit(main())


