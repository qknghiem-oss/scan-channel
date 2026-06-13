"""
LLM-Client — zentraler LLM-Zugriff für alle KI-Aufgaben im Projekt.

Alle Scripts, die KI brauchen, importieren von hier:
    from ollama_client import chat, synthesize, OLLAMA_URL

Primär: LiteLLM-Gateway auf dem VPS (http://litellm:4000)
  → deepseek-v4-flash  → schnelle Analyse, Kategorisierung
  → deepseek-v4-pro    → Synthese, Deep Dives (qualitativ)
  → kimi-k2.6          → Alternativ-Synthese

Fallback: Ollama direkt (http://ollama:11434 oder localhost:11434)
  → deepseek-v4-flash:cloud / deepseek-v4-pro:cloud (original Namen)
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# .env aus Projekt-Root laden
ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# LiteLLM (primär auf VPS)
LITELLM_URL = os.environ.get("LITELLM_URL", "http://litellm:4000")
LITELLM_KEY = os.environ.get("LITELLM_KEY", "")

# Ollama direkt (Fallback)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_URL_FALLBACK = "http://localhost:11434"

# Reihenfolge der Backends
BACKENDS = []
if LITELLM_KEY:
    BACKENDS.append(("litellm", f"{LITELLM_URL}/v1/chat/completions", LITELLM_KEY))
BACKENDS.append(("ollama", f"{OLLAMA_URL}/v1/chat/completions", ""))
BACKENDS.append(("ollama_local", f"{OLLAMA_URL_FALLBACK}/v1/chat/completions", ""))

# Modell-Auswahl (LiteLLM-Namen, ohne :cloud-Suffix)
MODEL_FAST = os.environ.get("OLLAMA_MODEL_FAST", "deepseek-v4-flash")
MODEL_PRO  = os.environ.get("OLLAMA_MODEL_PRO",  "deepseek-v4-pro")
MODEL_ALT  = os.environ.get("OLLAMA_MODEL_ALT",  "kimi-k2.6")


def _post(url: str, payload: dict, timeout: int = 120, api_key: str = "") -> dict:
    """HTTP-POST an OpenAI-kompatiblen Endpunkt."""
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(
    messages: list[dict],
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 180,
) -> str:
    """
    Sendet eine Chat-Anfrage an LiteLLM/Ollama. Gibt den Text der Antwort zurück.

    Probiert Backends in Reihenfolge: LiteLLM → Ollama Docker → Ollama localhost.
    """
    model = model or MODEL_PRO
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    last_error = None
    for name, endpoint, api_key in BACKENDS:
        try:
            result = _post(endpoint, payload, timeout=timeout, api_key=api_key)
            msg = result["choices"][0]["message"]
            # Deepseek chain-of-thought: content may be empty, real response in reasoning_content
            content = msg.get("content") or ""
            if not content.strip():
                content = msg.get("reasoning_content") or ""
            return content
        except urllib.error.URLError as e:
            last_error = e
            continue
        except KeyError as e:
            raise RuntimeError(f"Unerwartetes LLM-Response-Format ({name}): {e}") from e

    raise RuntimeError(
        f"Kein LLM-Backend erreichbar. "
        f"Geprüft: {[b[0] for b in BACKENDS]}. "
        f"Letzter Fehler: {last_error}"
    )


def synthesize(
    system_prompt: str,
    user_content: str,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 6000,
) -> str:
    """
    Synthesis-Shortcut: system + user Message, gibt Markdown-Text zurück.
    Für Section-Synthese und Deep Dives.
    """
    return chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
        model=model or MODEL_PRO,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=300,
    )


def analyze(
    prompt: str,
    model: str = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    Analyse-Shortcut: ein einzelner User-Prompt, deterministischer Output.
    Für Kategorisierung, Extraktion, Klassifikation.
    """
    return chat(
        messages=[{"role": "user", "content": prompt}],
        model=model or MODEL_FAST,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=60,
    )


def list_models() -> list[str]:
    """Listet alle verfügbaren Modelle (LiteLLM oder Ollama)."""
    # LiteLLM: OpenAI-kompatibler /models Endpunkt
    if LITELLM_KEY:
        try:
            headers = {"Authorization": f"Bearer {LITELLM_KEY}"}
            req = urllib.request.Request(f"{LITELLM_URL}/models", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m["id"] for m in data.get("data", [])]
        except urllib.error.URLError:
            pass

    # Ollama: /api/tags Endpunkt
    for base_url in [OLLAMA_URL, OLLAMA_URL_FALLBACK]:
        try:
            req = urllib.request.Request(f"{base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m["name"] for m in data.get("models", [])]
        except urllib.error.URLError:
            continue
    return []


def ping() -> tuple[bool, str]:
    """Prüft ob ein LLM-Backend erreichbar ist. Gibt (ok, url_oder_name) zurück."""
    # LiteLLM prüfen
    if LITELLM_KEY:
        try:
            headers = {"Authorization": f"Bearer {LITELLM_KEY}"}
            req = urllib.request.Request(f"{LITELLM_URL}/models", headers=headers)
            with urllib.request.urlopen(req, timeout=5):
                return True, f"LiteLLM @ {LITELLM_URL}"
        except urllib.error.URLError:
            pass

    # Ollama direkt prüfen
    for base_url in [OLLAMA_URL, OLLAMA_URL_FALLBACK]:
        try:
            req = urllib.request.Request(f"{base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5):
                return True, f"Ollama @ {base_url}"
        except urllib.error.URLError:
            continue
    return False, ""


if __name__ == "__main__":
    print(f"Ollama-Client Selbsttest")
    print(f"  Primary URL: {OLLAMA_URL}")
    print(f"  Fallback URL: {OLLAMA_URL_FALLBACK}")
    print(f"  Modell (Pro):  {MODEL_PRO}")
    print(f"  Modell (Fast): {MODEL_FAST}")
    print()

    ok, url = ping()
    if not ok:
        print("  FEHLER: Ollama nicht erreichbar!")
        sys.exit(1)

    print(f"  Verbindung OK: {url}")
    models = list_models()
    print(f"  Verfügbare Modelle ({len(models)}):")
    for m in models:
        print(f"    - {m}")
    print()

    print("  Test-Anfrage...")
    antwort = analyze("Antworte auf Deutsch mit genau einem Satz: Was ist künstliche Intelligenz?",
                      model=MODEL_FAST)
    print(f"  Antwort: {antwort}")
    print()
    print("  OK")
