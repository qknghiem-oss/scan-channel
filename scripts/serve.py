"""Threaded HTTP server + TTS Proxy mit MP3-Cache."""
import hashlib
import http.server
import json
import os
import re
import socketserver
import ssl
import sys
import subprocess
import threading
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

# .env laden
ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

PORT = 8765
SITE_DIR = ROOT / "site"
AUDIO_CACHE = ROOT / "data" / "audio_cache"
BOOK_FILE = SITE_DIR / "data" / "book.json"
DD_DIR = ROOT / "data" / "deep_dives"
DD_PENDING = DD_DIR / "pending"
DD_GENERATED = DD_DIR / "generated"
DD_DASHBOARD = DD_DIR / "dashboard_data"
PER_VIDEO_DIR = ROOT / "data" / "per_video_deep_dives"
PER_VIDEO_PENDING = PER_VIDEO_DIR / "pending"
PER_VIDEO_GENERATED = PER_VIDEO_DIR / "generated"
SYNC_STATE = ROOT / "data" / "sync_state.json"

# In-memory Job-Store für Sync-Status (verloren bei Server-Restart)
SYNC_JOBS = {}
UPDATE_JOBS = {}  # full pipeline update jobs (Phase 15)
SYNTHESIZE_JOBS = {}  # synthesis stub jobs

UPDATE_PHASE_NAMES = [
    ("SCAN",      "Channel-Sync"),
    ("ANALYZE",   "Regel-Analyse"),
    ("SITE_DATA", "Site-Daten"),
    ("BRIEFINGS", "Briefings"),
    ("ASSEMBLE",  "Buch-Index"),
    ("SYNC_DDS",  "Deep Dives einsyncen"),
    ("SITE_BOOK", "Site-Book bauen"),
    ("CONCEPT_IX","Konzept-Index"),
    ("AUTO_BOOK", "Auto-Bookmarks"),
]

ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVEN_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_flash_v2_5")
ELEVEN_DEFAULT_VOICE = os.environ.get("ELEVENLABS_DEFAULT_VOICE", "pNInz6obpgDQGcFmaJgB")

# Voice-Auswahl für die UI (Name → Voice-ID)
ELEVEN_VOICES = {
    "Adam (m, neutral)":      "pNInz6obpgDQGcFmaJgB",
    "George (m, ruhig)":      "JBFqnCBsd6RMkjVDRZzb",
    "Charlotte (w, warm)":    "XB0fDUnXU5powFXDhCwa",
    "Daniel (m, sachlich)":   "onwK4e9ZLuTAKqWW03F9",
    "Sarah (w, klar)":        "EXAVITQu4vr4xnSDxMaL",
}


def section_text(section_id: str) -> str:
    """Lese Section-Body aus book.json und bereinige für TTS."""
    if not BOOK_FILE.exists():
        return ""
    book = json.loads(BOOK_FILE.read_text(encoding="utf-8"))
    for ch in book["chapters"]:
        for s in ch["sections"]:
            if s["id"] == section_id:
                return clean_for_tts(s["body_md"])
    return ""


def clean_for_tts(text: str) -> str:
    """Bereinigt Markdown fuer TTS-Vortrag."""
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"^#+\s+(.*)", r"\1.", text, flags=re.MULTILINE)
    text = re.sub(r"\[\[[0-9.]+\s+([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r">+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def section_segments(section_id: str) -> list[dict]:
    """Teilt eine Sektion in Audio-Segmente auf — pro H2-Abschnitt eins.
       Returns: [{id, title, text}, ...]"""
    if not BOOK_FILE.exists():
        return []
    book = json.loads(BOOK_FILE.read_text(encoding="utf-8"))
    body_md = None
    for ch in book["chapters"]:
        for s in ch["sections"]:
            if s["id"] == section_id:
                body_md = s["body_md"]
                break
    if not body_md:
        return []

    # Frontmatter entfernen
    body_md = re.sub(r"^---\n.*?\n---\n", "", body_md, flags=re.DOTALL)

    # Splitte an H2-Marken
    parts = re.split(r"^(##\s+.+?)$", body_md, flags=re.MULTILINE)
    segments = []
    # parts[0] ist Intro vor erstem H2 (mit H1)
    if parts[0].strip():
        intro_text = parts[0]
        # H1 als Intro-Titel
        h1_match = re.match(r"^#\s+(.+)$", intro_text, re.MULTILINE)
        intro_title = h1_match.group(1) if h1_match else "Einleitung"
        intro_clean = clean_for_tts(intro_text)
        if intro_clean:
            segments.append({
                "id": f"seg-{len(segments)}",
                "title": intro_title,
                "text": intro_clean,
                "char_count": len(intro_clean),
                "type": "intro",
            })

    # H2-Abschnitte
    i = 1
    while i < len(parts) - 1:
        h2_line = parts[i]
        content = parts[i+1] if i+1 < len(parts) else ""
        title = re.sub(r"^##\s+", "", h2_line).strip()
        text_clean = clean_for_tts(h2_line + "\n" + content)
        if text_clean:
            segments.append({
                "id": f"seg-{len(segments)}",
                "title": title,
                "text": text_clean,
                "char_count": len(text_clean),
                "type": "section",
            })
        i += 2

    return segments


def cache_path(section_id: str, voice_id: str) -> Path:
    AUDIO_CACHE.mkdir(parents=True, exist_ok=True)
    # Kanonischer Key inkl. voice_id + model — Cache-Invalidation by file rename
    h = hashlib.md5(f"{section_id}|{voice_id}|{ELEVEN_MODEL}".encode()).hexdigest()[:10]
    return AUDIO_CACHE / f"{section_id}__{voice_id[:8]}__{h}.mp3"


def fetch_elevenlabs(text: str, voice_id: str) -> bytes:
    """Ruft ElevenLabs auf, gibt MP3-Bytes zurück."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = json.dumps({
        "text": text,
        "model_id": ELEVEN_MODEL,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("xi-api-key", ELEVEN_KEY)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "audio/mpeg")
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        return resp.read()


# Mapping ElevenLabs → edge-tts Stimme (Deutsch, mittlere Stufe)
EDGE_TTS_VOICE = "de-DE-SeraphinaMultilingualNeural"
EDGE_TTS_VOICE_HD = "de-DE-SeraphinaMultilingualNeural"

def fetch_edge_tts(text: str, hd: bool = False) -> bytes:
    """Fallback: Microsoft Edge TTS (kostenlos, kein API-Key nötig).
    Gibt MP3-Bytes zurück. Benötigt: pip install edge-tts"""
    import asyncio, tempfile, os
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError("edge-tts nicht installiert (pip install edge-tts)")

    voice = EDGE_TTS_VOICE_HD if hd else EDGE_TTS_VOICE

    async def _generate() -> bytes:
        communicate = edge_tts.Communicate(text, voice)
        buf = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.extend(chunk["data"])
        return bytes(buf)

    return asyncio.run(_generate())


def fetch_tts(text: str, voice_id: str = None, hd: bool = False) -> bytes:
    """TTS via Microsoft Edge (Seraphina) — kostenlos, kein API-Key."""
    return fetch_edge_tts(text, hd=hd)


class ThreadedHTTP(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 64


class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))

    # === Custom Routes ===

    def do_GET(self):
        # /tts/voices → Liste verfügbarer Stimmen
        if self.path == "/tts/voices":
            self._json_response({"voices": ELEVEN_VOICES, "default": ELEVEN_DEFAULT_VOICE, "model": ELEVEN_MODEL})
            return

        # /tts/audio?section=2.1&voice=... → MP3 (komplette Sektion, alt)
        # /tts/audio?section=2.1&seg=0&voice=... → MP3 nur eines Segments (neu)
        if self.path.startswith("/tts/audio"):
            self._handle_tts()
            return

        # /tts/segments?section=2.1 → Liste der Segmente
        if self.path.startswith("/tts/segments"):
            self._handle_segments()
            return

        # /deep-dive/list → pending + generated
        if self.path.startswith("/deep-dive/list"):
            self._handle_dd_list()
            return

        # /deep-dive/dashboard?topic=X → Dashboard-Daten
        if self.path.startswith("/deep-dive/dashboard"):
            self._handle_dd_dashboard()
            return

        # /scheduler/log → Protokoll der automatischen Jobs
        if self.path.startswith("/scheduler/log"):
            self._handle_scheduler_log()
            return

        # /sync/state → aktueller Sync-State
        if self.path.startswith("/sync/state"):
            self._handle_sync_state()
            return

        # /sync/status?job_id=... → Status eines Sync-Jobs
        if self.path.startswith("/sync/status"):
            self._handle_sync_status()
            return

        # /update/status?job_id=... → Status eines Full-Update-Jobs
        if self.path.startswith("/update/status"):
            self._handle_update_status()
            return

        # /synthesize/status → Liste aller offenen Synthese-Items
        if self.path.startswith("/synthesize/status"):
            self._handle_synthesize_status()
            return

        # /per-video/list → Liste der Per-Video Deep Dives
        if self.path.startswith("/per-video/list"):
            self._handle_per_video_list()
            return

        # /per-video/content?id=<video_id> → Markdown-Inhalt
        if self.path.startswith("/per-video/content"):
            self._handle_per_video_content()
            return

        # /praxis/index → aggregierter Praxis-Index (Layer 3)
        if self.path.startswith("/praxis/index"):
            self._handle_praxis_index()
            return

        # Static
        super().do_GET()

    def do_POST(self):
        if self.path == "/deep-dive/bookmark":
            self._handle_dd_bookmark()
            return
        if self.path == "/sync/trigger":
            self._handle_sync_trigger()
            return
        if self.path == "/update/trigger":
            self._handle_update_trigger()
            return
        if self.path == "/synthesize/trigger":
            self._handle_synthesize_trigger()
            return
        if self.path == "/per-video/bookmark":
            self._handle_per_video_bookmark()
            return
        if self.path == "/search/usecase":
            self._handle_usecase_search()
            return
        self.send_error(404, "POST endpoint not found")

    def do_DELETE(self):
        if self.path.startswith("/deep-dive/bookmark/"):
            self._handle_dd_delete()
            return
        self.send_error(404, "DELETE endpoint not found")

    def do_OPTIONS(self):
        # CORS-Preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error_response(self, msg, status=500):
        self._json_response({"error": msg}, status)

    def _handle_segments(self):
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        section_id = (q.get("section") or [""])[0]
        if not section_id:
            self._error_response("section parameter missing", 400)
            return
        segs = section_segments(section_id)
        # Schaetze Audio-Dauer (rough: 17 chars/sec bei rate=1.0)
        for s in segs:
            s["est_seconds"] = round(s["char_count"] / 17)
        self._json_response({"section_id": section_id, "segments": segs})

    def _handle_tts(self):
        # Parse Query
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        section_id = (q.get("section") or [""])[0]
        seg_idx_str = (q.get("seg") or [""])[0]
        voice_id = (q.get("voice") or [ELEVEN_DEFAULT_VOICE])[0]

        if not section_id:
            self._error_response("section parameter missing", 400)
            return
        if not ELEVEN_KEY:
            self._error_response("ELEVENLABS_API_KEY not set in .env", 500)
            return

        # Segment-Modus
        if seg_idx_str:
            try:
                seg_idx = int(seg_idx_str)
            except ValueError:
                self._error_response("invalid seg parameter", 400)
                return
            segs = section_segments(section_id)
            if seg_idx < 0 or seg_idx >= len(segs):
                self._error_response(f"segment {seg_idx} out of range (have {len(segs)})", 400)
                return
            text = segs[seg_idx]["text"]
            cache = cache_path(f"{section_id}_seg{seg_idx}", voice_id)
            if cache.exists():
                sys.stderr.write(f"  [TTS CACHE HIT] {section_id}/seg{seg_idx} voice={voice_id[:8]} size={cache.stat().st_size}\n")
                self._serve_mp3(cache)
                return
            try:
                sys.stderr.write(f"  [TTS GEN] {section_id}/seg{seg_idx} chars={len(text)} title='{segs[seg_idx]['title'][:30]}'\n")
                mp3 = fetch_tts(text, voice_id)
                cache.write_bytes(mp3)
                sys.stderr.write(f"  [TTS OK] segment bytes={len(mp3)}\n")
                self._serve_mp3(cache)
            except Exception as e:
                self._error_response(f"TTS generation failed: {e}", 500)
            return

        # Full-Section Modus (alt, abwaerts-kompatibel)
        cache = cache_path(section_id, voice_id)
        if cache.exists():
            sys.stderr.write(f"  [TTS CACHE HIT] {section_id} voice={voice_id[:8]} size={cache.stat().st_size}\n")
            self._serve_mp3(cache)
            return

        # Text holen
        text = section_text(section_id)
        if not text:
            self._error_response(f"section {section_id} not found", 404)
            return

        try:
            sys.stderr.write(f"  [TTS GEN] {section_id} voice={voice_id[:8]} chars={len(text)}\n")
            mp3 = fetch_tts(text, voice_id)
            cache.write_bytes(mp3)
            sys.stderr.write(f"  [TTS OK] {section_id} bytes={len(mp3)} cached={cache.name}\n")
            self._serve_mp3(cache)
        except Exception as e:
            sys.stderr.write(f"  [TTS EXCEPTION] {e}\n")
            self._error_response(f"TTS generation failed: {e}", 500)

    def _serve_mp3(self, path: Path):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    # === Deep-Dive Endpoints ===

    def _slugify(self, s: str) -> str:
        import unicodedata
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
        return s or "topic"

    def _handle_dd_bookmark(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            topic = (data.get("topic") or "").strip()
            type_ = (data.get("type") or "concept").strip()
            note = (data.get("note") or "").strip()
            if not topic:
                self._error_response("topic missing", 400)
                return
            DD_PENDING.mkdir(parents=True, exist_ok=True)
            slug = self._slugify(topic)
            # Prüfe Duplikat
            existing = list(DD_PENDING.glob(f"*__{slug}.json"))
            if existing:
                self._json_response({"status": "duplicate", "file": existing[0].name, "topic": topic})
                return
            from datetime import datetime
            ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            fname = f"{ts}__{slug}.json"
            payload = {
                "topic": topic, "type": type_, "note": note,
                "bookmarked_at": datetime.now().isoformat(),
                "slug": slug, "status": "pending",
            }
            (DD_PENDING / fname).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            sys.stderr.write(f"  [DD BOOKMARK] {topic} ({type_}) → {fname}\n")
            self._json_response({"status": "ok", "file": fname, "slug": slug, "topic": topic}, 201)
        except Exception as e:
            sys.stderr.write(f"  [DD BOOKMARK ERROR] {e}\n")
            self._error_response(str(e), 500)

    def _handle_dd_list(self):
        DD_PENDING.mkdir(parents=True, exist_ok=True)
        DD_GENERATED.mkdir(parents=True, exist_ok=True)
        pending = []
        for f in sorted(DD_PENDING.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                pending.append({"file": f.name, **d})
            except Exception:
                pass
        generated = []
        for f in sorted(DD_GENERATED.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                generated.append({"file": f.name, **d})
            except Exception:
                pass
        self._json_response({"pending": pending, "generated": generated})

    def _handle_dd_dashboard(self):
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        topic = (q.get("topic") or [""])[0]
        slug_param = (q.get("slug") or [""])[0]
        if not topic and not slug_param:
            self._error_response("topic or slug missing", 400)
            return
        slug = slug_param or self._slugify(topic)
        DD_DASHBOARD.mkdir(parents=True, exist_ok=True)
        cache = DD_DASHBOARD / f"{slug}.json"
        if cache.exists():
            self._json_response(json.loads(cache.read_text(encoding="utf-8")))
            return
        # Live aggregate
        try:
            import subprocess
            # Verwende das 09-Skript als Subprozess
            script = Path(__file__).parent / "09_deep_dive.py"
            # Für Live-Aggregat: erstelle ein temporaeres Bookmark-Memorystruct
            bookmark = {"topic": topic, "type": "concept"}
            # Direktes Aggregieren via Inline-Aufruf statt subprocess:
            sys.path.insert(0, str(script.parent))
            import importlib.util
            spec = importlib.util.spec_from_file_location("dd09", str(script))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            dashboard = mod.aggregate_dashboard(bookmark)
            self._json_response(dashboard)
        except Exception as e:
            sys.stderr.write(f"  [DD DASHBOARD ERROR] {e}\n")
            self._error_response(str(e), 500)

    def _handle_dd_delete(self):
        fname = self.path.replace("/deep-dive/bookmark/", "").split("?")[0]
        if "/" in fname or ".." in fname or not fname.endswith(".json"):
            self._error_response("invalid filename", 400)
            return
        path = DD_PENDING / fname
        if not path.exists():
            self._error_response("not found", 404)
            return
        path.unlink()
        self._json_response({"status": "deleted", "file": fname})

    # === SCHEDULER Endpoints ===

    def _handle_scheduler_log(self):
        """Liefert die letzten Scheduler-Job-Einträge."""
        log_file = ROOT / "data" / "scheduler_log.json"
        scheduler_state = ROOT / "data" / "scheduler_state.json"
        log_entries = []
        state = {}
        if log_file.exists():
            try:
                log_entries = json.loads(log_file.read_text(encoding="utf-8"))[-50:]
            except Exception:
                pass
        if scheduler_state.exists():
            try:
                state = json.loads(scheduler_state.read_text(encoding="utf-8"))
            except Exception:
                pass
        self._json_response({
            "state": state,
            "log": list(reversed(log_entries)),
        })

    # === SYNC Endpoints ===

    def _handle_sync_state(self):
        if SYNC_STATE.exists():
            state = json.loads(SYNC_STATE.read_text(encoding="utf-8"))
        else:
            state = {
                "last_sync_at": None,
                "known_video_ids": [],
                "pending_new_videos": [],
                "sync_history": [],
            }
        self._json_response(state)

    def _handle_sync_trigger(self):
        """Startet Sync im Hintergrund-Thread."""
        import subprocess
        job_id = uuid.uuid4().hex[:12]
        SYNC_JOBS[job_id] = {"status": "running", "progress": 0, "message": "Starting…", "started_at": datetime.now().isoformat(), "new_videos": []}

        def run_sync():
            try:
                SYNC_JOBS[job_id]["message"] = "Scanne Channel..."
                SYNC_JOBS[job_id]["progress"] = 10
                script = ROOT / "scripts" / "10_sync.py"
                proc = subprocess.Popen(
                    [sys.executable, str(script)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    cwd=str(ROOT), text=True, encoding="utf-8", errors="replace",
                )
                last_line = ""
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    last_line = line.strip()
                    if "NEUE Videos entdeckt" in line:
                        SYNC_JOBS[job_id]["message"] = last_line
                        SYNC_JOBS[job_id]["progress"] = 30
                    elif "Lade Transkript" in line:
                        SYNC_JOBS[job_id]["message"] = last_line
                        SYNC_JOBS[job_id]["progress"] = min(80, SYNC_JOBS[job_id]["progress"] + 5)
                    elif "SYNC FERTIG" in line:
                        SYNC_JOBS[job_id]["message"] = "Done"
                        SYNC_JOBS[job_id]["progress"] = 95
                proc.wait()
                # Final state holen
                if SYNC_STATE.exists():
                    state = json.loads(SYNC_STATE.read_text(encoding="utf-8"))
                    SYNC_JOBS[job_id]["new_videos"] = state.get("pending_new_videos", [])
                SYNC_JOBS[job_id]["status"] = "done" if proc.returncode == 0 else "failed"
                SYNC_JOBS[job_id]["progress"] = 100
                SYNC_JOBS[job_id]["finished_at"] = datetime.now().isoformat()
            except Exception as e:
                SYNC_JOBS[job_id]["status"] = "failed"
                SYNC_JOBS[job_id]["message"] = f"Error: {e}"

        threading.Thread(target=run_sync, daemon=True).start()
        self._json_response({"job_id": job_id, "status": "running"}, 202)

    def _handle_sync_status(self):
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        job_id = (q.get("job_id") or [""])[0]
        if not job_id or job_id not in SYNC_JOBS:
            self._error_response("job not found", 404)
            return
        self._json_response(SYNC_JOBS[job_id])

    # === Full Update (Phase 15) ===

    def _handle_update_trigger(self):
        """Startet voller Channel-Update via 15_full_update.py."""
        import subprocess
        job_id = str(uuid.uuid4())
        UPDATE_JOBS[job_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "phases": [
                {"n": i+1, "id": pid, "name": pname, "status": "pending", "logs": [], "duration_s": None}
                for i, (pid, pname) in enumerate(UPDATE_PHASE_NAMES)
            ],
            "current_phase": 0,
            "current_message": "Wird gestartet…",
            "new_videos": [],
        }

        def run_update():
            script = ROOT / "scripts" / "15_full_update.py"
            try:
                proc = subprocess.Popen(
                    [sys.executable, str(script)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    bufsize=1, cwd=str(ROOT),
                )
                job = UPDATE_JOBS[job_id]
                for line in proc.stdout:
                    line = line.rstrip()
                    if not line:
                        continue
                    # Parse PHASE:n:event:data and UPDATE:event:data
                    if line.startswith("PHASE:"):
                        parts = line.split(":", 3)
                        if len(parts) >= 3:
                            n = int(parts[1]) - 1
                            event = parts[2]
                            data = parts[3] if len(parts) > 3 else ""
                            if 0 <= n < len(job["phases"]):
                                p = job["phases"][n]
                                if event == "start":
                                    p["status"] = "running"
                                    job["current_phase"] = n + 1
                                    job["current_message"] = data.split("|", 1)[-1] if "|" in data else p["name"]
                                elif event == "log":
                                    p["logs"].append(data[:160])
                                    if len(p["logs"]) > 40:
                                        p["logs"] = p["logs"][-40:]
                                    job["current_message"] = data[:120]
                                elif event == "done":
                                    p["status"] = "done"
                                    try:
                                        p["duration_s"] = float(data.split(":")[-1])
                                    except Exception:
                                        pass
                                elif event == "fail":
                                    p["status"] = "failed"
                                    job["status"] = "failed"
                                    job["current_message"] = f"Phase {n+1} fehlgeschlagen: {data}"
                                elif event == "skipped":
                                    p["status"] = "skipped"
                    elif line.startswith("UPDATE:"):
                        parts = line.split(":", 2)
                        event = parts[1] if len(parts) > 1 else ""
                        data = parts[2] if len(parts) > 2 else ""
                        if event == "done":
                            job["status"] = "done"
                            job["finished_at"] = datetime.now().isoformat()
                            job["total_duration_s"] = float(data) if data else None
                            job["current_message"] = f"Alle Phasen abgeschlossen ({data}s)"
                        elif event == "fail":
                            job["status"] = "failed"
                            job["finished_at"] = datetime.now().isoformat()
                            job["current_message"] = f"Update abgebrochen: {data}"
                proc.wait()
                if SYNC_STATE.exists():
                    state = json.loads(SYNC_STATE.read_text(encoding="utf-8"))
                    job["new_videos"] = state.get("pending_new_videos", [])
                if job["status"] == "running":
                    # fallback: process beendet ohne UPDATE:done
                    job["status"] = "done" if proc.returncode == 0 else "failed"
                    job["finished_at"] = datetime.now().isoformat()
            except Exception as e:
                UPDATE_JOBS[job_id]["status"] = "failed"
                UPDATE_JOBS[job_id]["current_message"] = f"Error: {e}"

        threading.Thread(target=run_update, daemon=True).start()
        self._json_response({"job_id": job_id, "status": "started", "phase_count": len(UPDATE_PHASE_NAMES)})

    def _handle_update_status(self):
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        job_id = (q.get("job_id") or [""])[0]
        if not job_id or job_id not in UPDATE_JOBS:
            self._error_response("job not found", 404)
            return
        self._json_response(UPDATE_JOBS[job_id])

    # === Synthesize (Stub) ===

    def _handle_synthesize_status(self):
        """Liefert Listing was synthetisierbar ist (Briefings ohne Sektion + pending DDs + pending Videos)."""
        pending_topic_dds = []
        pending_video_dds = []
        new_videos_without_section = []

        # Pending Topic DDs
        if DD_PENDING.exists():
            for f in DD_PENDING.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    pending_topic_dds.append({"topic": data.get("topic"), "slug": data.get("slug"), "priority": data.get("priority")})
                except Exception:
                    pass

        # Pending Per-Video DDs
        if PER_VIDEO_PENDING.exists():
            for f in PER_VIDEO_PENDING.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    pending_video_dds.append({"video_id": data.get("video_id"), "title": data.get("title", "")[:80]})
                except Exception:
                    pass

        # Neue Videos die noch keine Sektion haben (aus sync_state)
        if SYNC_STATE.exists():
            state = json.loads(SYNC_STATE.read_text(encoding="utf-8"))
            new_videos_without_section = state.get("pending_new_videos", [])

        self._json_response({
            "pending_topic_dds": pending_topic_dds,
            "pending_video_dds": pending_video_dds,
            "new_videos_without_section": new_videos_without_section,
            "totals": {
                "topic_dds": len(pending_topic_dds),
                "video_dds": len(pending_video_dds),
                "new_videos": len(new_videos_without_section),
            },
            "synth_available": False,  # Phase 2: Backend-Agent-Spawning noch nicht implementiert
            "note": "Phase 2 (Auto-Synthese via Agent-Spawning) ist in Vorbereitung. Aktuell: 'Mache die offenen Deep Dives' im Chat aufrufen.",
        })

    def _handle_synthesize_trigger(self):
        """Stub für später: triggert Synthese via Backend-Agent-Job."""
        import uuid
        job_id = str(uuid.uuid4())
        SYNTHESIZE_JOBS[job_id] = {
            "status": "not_implemented",
            "started_at": datetime.now().isoformat(),
            "message": (
                "Synthese-Backend ist in Vorbereitung. Aktuell: "
                "im Chat 'Mache die offenen Deep Dives' aufrufen — "
                "Claude spawnt parallele Agents je Bookmark."
            ),
        }
        self._json_response({"job_id": job_id, **SYNTHESIZE_JOBS[job_id]})

    # === Per-Video Deep Dive ===

    def _handle_per_video_list(self):
        PER_VIDEO_PENDING.mkdir(parents=True, exist_ok=True)
        PER_VIDEO_GENERATED.mkdir(parents=True, exist_ok=True)
        pending = []
        for f in sorted(PER_VIDEO_PENDING.glob("*.json")):
            try:
                pending.append({"file": f.name, **json.loads(f.read_text(encoding="utf-8"))})
            except Exception:
                pass
        generated = []
        for f in sorted(PER_VIDEO_GENERATED.glob("*.json")):
            try:
                generated.append({"file": f.name, **json.loads(f.read_text(encoding="utf-8"))})
            except Exception:
                pass
        self._json_response({"pending": pending, "generated": generated})

    def _handle_per_video_content(self):
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        video_id = (q.get("id") or [""])[0].strip()
        if not video_id or "/" in video_id or ".." in video_id:
            self._error_response("invalid id", 400)
            return
        md_path = PER_VIDEO_GENERATED / f"{video_id}.md"
        if not md_path.exists():
            self._error_response("not found", 404)
            return
        body = md_path.read_text(encoding="utf-8")
        self._json_response({"video_id": video_id, "markdown": body})

    def _handle_per_video_bookmark(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            video_id = (data.get("video_id") or "").strip()
            if not video_id:
                self._error_response("video_id missing", 400)
                return
            PER_VIDEO_PENDING.mkdir(parents=True, exist_ok=True)
            fname = f"{video_id}.json"
            path = PER_VIDEO_PENDING / fname
            if path.exists():
                self._json_response({"status": "duplicate", "file": fname})
                return
            payload = {
                "video_id": video_id,
                "title": (data.get("title") or "").strip(),
                "category": (data.get("category") or "").strip(),
                "bookmarked_at": datetime.now().isoformat(),
                "status": "pending",
                "type": "per_video",
            }
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            sys.stderr.write(f"  [PER-VIDEO BOOKMARK] {video_id} → {fname}\n")
            self._json_response({"status": "ok", "file": fname, "video_id": video_id}, 201)
        except Exception as e:
            self._error_response(str(e), 500)


    def _handle_praxis_index(self):
        praxis_file = ROOT / "data" / "praxis" / "praxis_index.json"
        if praxis_file.exists():
            self._json_response(json.loads(praxis_file.read_text(encoding="utf-8")))
        else:
            # Fallback: direkt aus videos_full.json bauen
            videos_file = ROOT / "data" / "videos_full.json"
            if not videos_file.exists():
                self._json_response({"total_items": 0, "all_items": [], "by_category": {}})
                return
            data = json.loads(videos_file.read_text(encoding="utf-8"))
            videos = data.get("videos", [])
            all_items = []
            for v in videos:
                for item in v.get("praxis_items", []):
                    all_items.append({**item,
                        "video_id": v.get("id", ""),
                        "video_title": v.get("title", ""),
                        "video_category": v.get("category", ""),
                        "source_url": v.get("source_url", ""),
                    })
            by_category = {}
            for it in all_items:
                cat = it.get("category", "technik")
                by_category.setdefault(cat, []).append(it)
            self._json_response({
                "generated_at": datetime.now().isoformat(),
                "total_items": len(all_items),
                "all_items": all_items,
                "by_category": by_category,
            })


    def _handle_usecase_search(self):
        """POST /search/usecase — KI-gestützte Anwendungsfall-Suche über alle Wissensschichten."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            query = (body.get("query") or "").strip()
            if not query:
                self._error_response("query missing", 400)
                return

            # 1. Praxis-Items laden
            praxis_items = []
            praxis_file = ROOT / "data" / "praxis" / "praxis_index.json"
            if praxis_file.exists():
                pdata = json.loads(praxis_file.read_text(encoding="utf-8"))
                praxis_items = pdata.get("all_items", [])

            # 2. Buch-Sektionen laden
            sections = []
            book_file = SITE_DIR / "data" / "book.json"
            if book_file.exists():
                book = json.loads(book_file.read_text(encoding="utf-8"))
                for ch in book.get("chapters", []):
                    for s in ch.get("sections", []):
                        sections.append({
                            "id":    s.get("id",""),
                            "title": s.get("title",""),
                            "body_preview": (s.get("body_md",""))[:300],
                        })

            # 3. Deep Dives laden (generierte)
            dds = []
            for f in sorted(DD_GENERATED.glob("*.json")):
                try:
                    d = json.loads(f.read_text(encoding="utf-8"))
                    dds.append({
                        "slug":  f.stem,
                        "topic": d.get("topic",""),
                        "type":  d.get("type",""),
                        "section_id": d.get("section_id",""),
                    })
                except Exception:
                    pass

            # Keyword-Fallback (schnell, immer verfügbar)
            q_lower = query.lower()
            q_words = [w for w in q_lower.split() if len(w) > 2]

            def keyword_score(text: str) -> int:
                t = text.lower()
                return sum(w in t for w in q_words)

            praxis_scored = sorted([
                {**it, "_score": keyword_score(it.get("text","") + " " + it.get("kontext","") + " " + it.get("video_title",""))}
                for it in praxis_items
            ], key=lambda x: x["_score"], reverse=True)

            sections_scored = sorted([
                {**s, "_score": keyword_score(s.get("title","") + " " + s.get("body_preview",""))}
                for s in sections
            ], key=lambda x: x["_score"], reverse=True)

            dds_scored = sorted([
                {**d, "_score": keyword_score(d.get("topic",""))}
                for d in dds
            ], key=lambda x: x["_score"], reverse=True)

            # Keyword-Ergebnisse (Top 5 pro Kategorie, nur mit Score > 0)
            kw_praxis   = [x for x in praxis_scored   if x["_score"] > 0][:8]
            kw_sections = [x for x in sections_scored if x["_score"] > 0][:5]
            kw_dds      = [x for x in dds_scored      if x["_score"] > 0][:5]

            # 4. LLM-Semantic-Search (nur auf VPS mit LITELLM_KEY, sofort skippen sonst)
            llm_results = None
            try:
                import os as _os
                _litellm_key = _os.environ.get("LITELLM_KEY", "")
                if not _litellm_key:
                    raise RuntimeError("LITELLM_KEY not set, skip LLM search")

                sys.path.insert(0, str(Path(__file__).parent))
                from ollama_client import synthesize, MODEL_FAST

                compact_praxis = "\n".join([
                    f"P{i}: {it.get('text','')} [{it.get('category','')}]"
                    for i, it in enumerate(praxis_items[:50])
                ])
                compact_sections = "\n".join([
                    f"S{i}: {s.get('title','')} ({s.get('id','')})"
                    for i, s in enumerate(sections[:80])
                ])
                compact_dds = "\n".join([
                    f"D{i}: {d.get('topic','')}"
                    for i, d in enumerate(dds[:30])
                ])

                system = """Du bist ein Wissens-Assistent. Analysiere die Nutzeranfrage und finde
die passendsten Einträge aus den verfügbaren Wissensquellen.

Antworte NUR mit JSON (kein Markdown):
{
  "praxis_ids": [0,1,2],
  "section_ids": [0,1,2],
  "dd_ids": [0,1],
  "erklaerung": "1-2 Sätze warum diese Treffer passen"
}

Wähle maximal 5 Praxis-Items, 4 Buch-Sektionen, 3 Deep Dives.
Nur wirklich relevante Treffer — lieber wenige gute als viele schlechte."""

                user_msg = f"""NUTZERANFRAGE: {query}

VERFÜGBARE PRAXIS-ITEMS (Index: Inhalt [Kategorie]):
{compact_praxis}

VERFÜGBARE BUCH-SEKTIONEN (Index: Titel (ID)):
{compact_sections}

VERFÜGBARE DEEP DIVES (Index: Thema):
{compact_dds}

Welche Einträge passen am besten zur Anfrage?"""

                llm_raw = synthesize(system, user_msg, model=MODEL_FAST,
                                     temperature=0.1, max_tokens=2000)

                # JSON aus Antwort extrahieren — robust gegen Chain-of-Thought
                import re as _re
                text = llm_raw.strip()
                text = _re.sub(r"```[a-z]*\n?", "", text).replace("```", "")
                # Suche {..."praxis_ids"...} — auch mit verschachtelten Werten
                idx = text.rfind('"praxis_ids"')
                if idx == -1:
                    raise ValueError(f"Kein JSON-Block gefunden: {text[:200]}")
                # gehe rückwärts zum öffnenden {
                brace_start = text.rfind("{", 0, idx)
                if brace_start == -1:
                    raise ValueError("Kein { vor praxis_ids")
                # finde schließende } (zähle Klammerntiefe)
                depth, brace_end = 0, -1
                for ci, ch in enumerate(text[brace_start:], brace_start):
                    if ch == "{": depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            brace_end = ci + 1
                            break
                if brace_end == -1:
                    raise ValueError("Kein schließendes } gefunden")
                parsed = json.loads(text[brace_start:brace_end])

                # Index-Normalisierung: Modell gibt manchmal "P0","S1" statt 0,1
                def _norm_ids(ids, prefix):
                    result = []
                    for x in ids:
                        if isinstance(x, int):
                            result.append(x)
                        elif isinstance(x, str) and x.startswith(prefix):
                            try:
                                result.append(int(x[len(prefix):]))
                            except ValueError:
                                pass
                    return result

                llm_results = {
                    "praxis": [praxis_items[i] for i in _norm_ids(parsed.get("praxis_ids",[]), "P") if i < len(praxis_items)],
                    "sections": [sections[i] for i in _norm_ids(parsed.get("section_ids",[]), "S") if i < len(sections)],
                    "dds": [dds[i] for i in _norm_ids(parsed.get("dd_ids",[]), "D") if i < len(dds)],
                    "erklaerung": parsed.get("erklaerung",""),
                }
            except Exception as e:
                sys.stderr.write(f"  [SEARCH LLM] Fehler: {e}\n")

            self._json_response({
                "query": query,
                "keyword": {
                    "praxis": kw_praxis,
                    "sections": kw_sections,
                    "dds": kw_dds,
                },
                "semantic": llm_results,
            })
        except Exception as e:
            self._error_response(str(e), 500)


def _kill_port(port: int):
    """Kill any process already listening on port (Windows + Unix)."""
    try:
        import platform
        if platform.system() == "Windows":
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL
            )
            pids = set()
            for line in out.splitlines():
                if f":{port}" in line and "LISTEN" in line.upper():
                    parts = line.split()
                    try:
                        pids.add(int(parts[-1]))
                    except ValueError:
                        pass
            own = os.getpid()
            for pid in pids:
                if pid != own:
                    subprocess.call(
                        ["taskkill", "/PID", str(pid), "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    print(f"  [serve] killed stale PID {pid} on :{port}")
        else:
            out = subprocess.check_output(
                ["fuser", str(port) + "/tcp"], text=True, stderr=subprocess.DEVNULL
            )
            own = os.getpid()
            for pid_s in out.split():
                try:
                    pid = int(pid_s)
                    if pid != own:
                        os.kill(pid, 9)
                        print(f"  [serve] killed stale PID {pid} on :{port}")
                except ValueError:
                    pass
    except Exception:
        pass


if __name__ == "__main__":
    _kill_port(PORT)
    os.chdir(str(SITE_DIR))
    AUDIO_CACHE.mkdir(parents=True, exist_ok=True)
    host = "0.0.0.0" if os.environ.get("SERVE_PUBLIC") else "127.0.0.1"
    print(f"Serving {SITE_DIR} on http://{host}:{PORT}")
    print(f"Audio cache: {AUDIO_CACHE}")
    print(f"ElevenLabs Key: {'OK (' + ELEVEN_KEY[:10] + '...)' if ELEVEN_KEY else 'MISSING (set ELEVENLABS_API_KEY in .env)'}")
    print(f"ElevenLabs Model: {ELEVEN_MODEL}")
    sys.stdout.flush()
    with ThreadedHTTP((host, PORT), Handler) as httpd:
        httpd.serve_forever()
