"""
00_init_channel.py — erstellt channel.config.json + Projektstruktur fuer einen
neuen YouTube-Channel.

Aufruf:
    python 00_init_channel.py --url <CHANNEL_URL> --name "<NAME>" --output <DIR> [--days 90]

Beispiel:
    python 00_init_channel.py \
        --url https://www.youtube.com/@everlastai/videos \
        --name "Everlast AI" \
        --output ./everlast_knowledge \
        --days 90
"""

import argparse
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


TEMPLATE = {
    "channel_url": "",
    "channel_name": "",
    "handle": "",
    "language": "de",
    "days_back": 90,
    "category_keywords": {
        "tools": ["tool", "stack"],
        "interview": ["interview", "gespraech", "im gespraech"],
        "tutorial": ["tutorial", "kurs", "guide", "anleitung"],
        "news": ["news", "update", "neu"],
        "business": ["business", "geschaeft", "umsatz", "wirtschaft"]
    },
    "known_entities": {
        "people": [],
        "tools": [],
        "companies": [],
        "concepts": []
    },
    "book_meta": {
        "title": "Wissensbuch <NAME> <JAHR>",
        "subtitle": "Eine Lesereise durch den Channel",
        "style": "narrativ-erzaehlend"
    },
    "tts": {
        "enabled": True,
        "default_voice": "pNInz6obpgDQGcFmaJgB",
        "model": "eleven_flash_v2_5"
    }
}


def main():
    parser = argparse.ArgumentParser(description="Initialisiert einen neuen Channel-Workspace")
    parser.add_argument("--url", required=True, help="YouTube-Channel-URL (z.B. https://youtube.com/@channelname/videos)")
    parser.add_argument("--name", required=True, help="Anzeige-Name des Channels")
    parser.add_argument("--output", required=True, help="Ziel-Verzeichnis (wird angelegt)")
    parser.add_argument("--days", type=int, default=90, help="Anzahl Tage rueckwaerts (default 90)")
    parser.add_argument("--handle", help="Channel-Handle (@channelname), optional")
    args = parser.parse_args()

    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "data").mkdir(exist_ok=True)
    (out / "scripts").mkdir(exist_ok=True)
    (out / "site").mkdir(exist_ok=True)

    # Handle aus URL extrahieren wenn nicht gegeben
    handle = args.handle
    if not handle and "@" in args.url:
        handle = "@" + args.url.split("@")[1].split("/")[0]

    config = dict(TEMPLATE)
    config["channel_url"] = args.url
    config["channel_name"] = args.name
    config["handle"] = handle or ""
    config["days_back"] = args.days
    config["book_meta"]["title"] = config["book_meta"]["title"].replace("<NAME>", args.name)
    config["book_meta"]["title"] = config["book_meta"]["title"].replace("<JAHR>", "2026")

    config_path = out / "channel.config.json"
    if config_path.exists():
        print(f"WARNUNG: {config_path} existiert bereits. Ueberschreiben? (y/n)")
        if input().strip().lower() != "y":
            print("Abgebrochen.")
            return
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"OK Channel-Konfiguration angelegt:")
    print(f"   Datei: {config_path}")
    print(f"   Channel: {args.name} ({handle})")
    print(f"   URL: {args.url}")
    print(f"   Tage: {args.days}")
    print()
    print("Naechste Schritte:")
    print(f"   1. cd {out}")
    print(f"   2. Skripte 01-08 kopieren aus dem Skill-Repo")
    print(f"   3. python scripts/01_scan_channel.py")
    print(f"   4. python scripts/02_extract_transcripts.py")
    print(f"   5. ... (siehe SKILL.md)")


if __name__ == "__main__":
    main()
