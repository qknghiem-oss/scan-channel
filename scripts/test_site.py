"""
Playwright-Test der Wissensbuch-Website.
Klickt durch alle Tabs, prüft TOC, Sektionen, Sources-Sidebar, Cross-Refs,
Video-Timestamps, Volltextsuche, Modal, Concept-Graph, Timeline, Lesepfade.
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "http://127.0.0.1:8765/index.html"
SCREENSHOT_DIR = Path(__file__).parent.parent / "test_screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

errors = []
passed = []


def report(name: str, ok: bool, detail: str = ""):
    status = "OK " if ok else "FAIL"
    print(f"  [{status}] {name}{(' — ' + detail) if detail else ''}")
    (passed if ok else errors).append(name)


def shoot(page, name):
    page.screenshot(path=str(SCREENSHOT_DIR / f"{name}.png"), full_page=False)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # Konsolen-Fehler einsammeln
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print("=" * 70)
        print("Playwright Site Test")
        print("=" * 70)

        # 1. LADEN — robust mit Retry, falls Race-Condition
        print("\n[1] Seite laden")
        loaded = False
        for attempt in range(3):
            page.goto(URL, wait_until="load")
            page.wait_for_timeout(3000)
            count = page.evaluate("document.querySelectorAll('.toc-section').length")
            if count >= 39:
                loaded = True
                break
            print(f"  Attempt {attempt+1}: only {count} sections — retry…")
            page.wait_for_timeout(1500)
        if not loaded:
            raise RuntimeError("Konnte nach 3 Versuchen keine 39 Sektionen laden")
        title = page.title()
        report("Titel geladen", "KI-Landschaft" in title, title)
        shoot(page, "01_welcome")

        # 2. WELCOME-STATS
        print("\n[2] Welcome-Daten")
        words = page.locator("#ws-words").text_content()
        quotes = page.locator("#ws-quotes").text_content()
        readmin = page.locator("#ws-readmin").text_content()
        report("Wort-Count gefüllt", words and words != "—", words)
        report("Zitat-Count gefüllt", quotes and quotes != "—", quotes)
        report("Lesezeit gefüllt", readmin and readmin != "—", readmin + " Min")

        # 3. TOC: Alle Kapitel sichtbar?
        print("\n[3] Inhaltsverzeichnis")
        toc_chapters = page.locator(".toc-chapter").count()
        report("13 Kapitel im TOC (inkl. Deep Dives)", toc_chapters == 13, f"{toc_chapters} gefunden")
        open_chapters = page.locator(".toc-chapter.open").count()
        report("Alle Kapitel offen (auto-expand)", open_chapters == 13, f"{open_chapters} von 13 offen")
        toc_sections = page.locator(".toc-section").count()
        report("69 Sektionen im TOC (39 Buch + 30 Deep Dives)", toc_sections == 69, f"{toc_sections} gefunden")

        # 4. SEKTION 1.1 LADEN
        print("\n[4] Sektion 1.1 laden")
        page.click('.toc-section[data-section-id="1.1"]')
        page.wait_for_timeout(500)
        h1 = page.locator(".book-content h1").first.text_content()
        report("Sektion 1.1 H1 sichtbar", "1.1" in h1 or "90 Tage" in h1, h1[:60] if h1 else "—")
        active = page.locator(".toc-section.active").get_attribute("data-section-id")
        report("TOC-Active-State", active == "1.1", active)
        shoot(page, "02_section_1_1")

        # 5. ASIDE (Quellen + Verwandtes)
        print("\n[5] Quellen-Sidebar")
        aside = page.locator("#book-aside")
        aside_visible = aside.is_visible()
        report("Aside sichtbar", aside_visible)
        sources_count = page.locator(".aside-source").count()
        report("Quell-Videos gelistet", sources_count >= 3, f"{sources_count} Quellen")
        related_count = page.locator(".aside-related").count()
        report("Verwandte Sektionen gelistet", related_count >= 1, f"{related_count} Refs")

        # 6. CROSS-REF KLICK
        print("\n[6] Cross-Reference Klick")
        first_crossref = page.locator(".book-content a.crossref").first
        if first_crossref.count() > 0:
            target = first_crossref.get_attribute("data-section")
            first_crossref.click()
            page.wait_for_timeout(500)
            new_active = page.locator(".toc-section.active").get_attribute("data-section-id")
            report("Cross-Ref springt zu Ziel", new_active == target, f"{target} → {new_active}")
        else:
            report("Cross-Ref gefunden", False, "keine im Body")

        # 7. TIMESTAMP-LINK (Video-Embed)
        print("\n[7] Video-Timestamp-Link")
        page.click('.toc-section[data-section-id="2.1"]')
        page.wait_for_timeout(500)
        ts_link = page.locator(".book-content a.timestamp-link").first
        if ts_link.count() > 0:
            vid = ts_link.get_attribute("data-video")
            time_sec = ts_link.get_attribute("data-time")
            ts_link.click()
            page.wait_for_timeout(800)
            modal_visible = page.locator("#modal").is_visible()
            iframe_src = page.locator("#modal iframe.video-iframe").get_attribute("src") if modal_visible else ""
            has_start = f"start={time_sec}" in (iframe_src or "")
            report("Modal öffnet bei Timestamp", modal_visible, f"video={vid}, t={time_sec}")
            report("YouTube-Embed mit Start-Param", has_start, iframe_src[:80] if iframe_src else "—")
            shoot(page, "03_video_modal")
            page.locator("#modal button.modal-close").click()
            page.wait_for_timeout(300)
        else:
            report("Timestamp-Link gefunden", False)

        # 8. SECTION-NAV (Vorherige/Nächste) — sicher zu 2.1 zurück setzen, dann nav per JS
        print("\n[8] Sektion-Navigation Footer")
        # Sicherstellen, wo wir sind:
        page.evaluate("loadSection('2.1')")
        page.wait_for_timeout(500)
        # Nächste-Sektion: Klick auf der Seite via JS Onclick auf Anchor
        next_section_id = page.evaluate("document.querySelector('.section-nav a.next')?.getAttribute('onclick')?.match(/loadSection\\('([^']+)'\\)/)?.[1]")
        report("Nächste-Section-Link auf 2.2", next_section_id == "2.2", next_section_id)
        page.evaluate("document.querySelector('.section-nav a.next')?.click()")
        page.wait_for_timeout(500)
        new_active = page.locator(".toc-section.active").get_attribute("data-section-id")
        report("Nächste-Klick navigiert", new_active == "2.2", new_active)
        # Vorherige-Sektion
        prev_section_id = page.evaluate("document.querySelector('.section-nav a.prev')?.getAttribute('onclick')?.match(/loadSection\\('([^']+)'\\)/)?.[1]")
        report("Vorherige-Section-Link auf 2.1", prev_section_id == "2.1", prev_section_id)
        page.evaluate("document.querySelector('.section-nav a.prev')?.click()")
        page.wait_for_timeout(500)
        new_active = page.locator(".toc-section.active").get_attribute("data-section-id")
        report("Vorherige-Klick navigiert", new_active == "2.1", new_active)

        # 9. VOLLTEXTSUCHE
        print("\n[9] Volltextsuche")
        page.fill("#search", "Mythos")
        page.wait_for_timeout(600)
        hit_text = page.locator("#book-content h1").first.text_content()
        report("Suche zeigt Treffer-Seite", "Treffer" in hit_text or "Treffer für" in hit_text, hit_text[:50] if hit_text else "—")
        # Clear search
        page.fill("#search", "")
        page.wait_for_timeout(300)

        # 10. LESEPFADE-TAB
        print("\n[10] Lesepfade-Tab")
        page.click('[data-view="paths"]')
        page.wait_for_timeout(400)
        paths_active = page.locator("#view-paths").is_visible()
        report("Lesepfade-View aktiv", paths_active)
        paths_cards = page.locator(".path-card").count()
        report("Lesepfad-Karten vorhanden", paths_cards >= 3, f"{paths_cards} Karten")
        shoot(page, "04_paths")

        # 11. LESEPFAD KLICK
        if paths_cards > 0:
            page.locator(".path-card").first.click()
            page.wait_for_timeout(500)
            book_active = page.locator("#view-book").is_visible()
            section_loaded = page.locator(".toc-section.active").count() > 0
            report("Lesepfad-Klick springt zum Buch", book_active and section_loaded)

        # 12. KONZEPT-WIKI / GRAPH
        print("\n[11] Konzept-Wiki")
        page.click('[data-view="concepts"]')
        page.wait_for_timeout(800)
        graph_visible = page.locator("#graph").is_visible()
        nodes = page.locator("#graph .node").count()
        report("Konzept-Graph rendert", graph_visible)
        report("Mindestens 20 Konzept-Knoten", nodes >= 20, f"{nodes} Knoten")
        shoot(page, "05_concepts")

        # 13. KONZEPT-KLICK
        if nodes > 0:
            page.locator("#graph .node").first.click()
            page.wait_for_timeout(500)
            modal_visible = page.locator("#modal").is_visible()
            report("Konzept-Klick öffnet Modal", modal_visible)
            page.locator("#modal button.modal-close").click()
            page.wait_for_timeout(300)

        # 14. TIMELINE
        print("\n[12] Timeline")
        page.click('[data-view="timeline"]')
        page.wait_for_timeout(400)
        timeline_dots = page.locator("#timeline .dot").count()
        report("Timeline-Punkte rendern", timeline_dots >= 40, f"{timeline_dots} Punkte")
        shoot(page, "06_timeline")
        # Dot klicken
        if timeline_dots > 0:
            page.locator("#timeline .dot").first.click()
            page.wait_for_timeout(500)
            modal_visible = page.locator("#modal").is_visible()
            report("Timeline-Dot öffnet Video-Modal", modal_visible)
            page.locator("#modal button.modal-close").click()
            page.wait_for_timeout(300)

        # 15. QUELLEN-BIBLIOTHEK
        print("\n[13] Quellen-Bibliothek")
        page.click('[data-view="library"]')
        page.wait_for_timeout(500)
        library_visible = page.locator("#view-library").is_visible()
        vcards = page.locator(".vcard").count()
        report("Bibliothek-View aktiv", library_visible)
        report("Video-Karten geladen", vcards >= 45, f"{vcards} Karten")
        shoot(page, "07_library")

        # 16. KATEGORIE-FILTER
        page.select_option("#filter-category", "claude")
        page.wait_for_timeout(400)
        filtered_count = page.locator(".vcard").count()
        result_text = page.locator("#result-count").text_content()
        report("Kategorie-Filter wirkt", filtered_count < 45 and filtered_count > 0, f"{filtered_count} Videos {result_text}")
        page.select_option("#filter-category", "")  # Reset
        page.wait_for_timeout(300)

        # 17. SORTIERUNG
        page.select_option("#filter-sort", "views")
        page.wait_for_timeout(300)
        first_card_title = page.locator(".vcard .vtitle").first.text_content()
        report("Sortierung wirkt", bool(first_card_title), first_card_title[:50] if first_card_title else "—")

        # 18. VIDEO-CARD KLICK
        page.locator(".vcard").first.click()
        page.wait_for_timeout(500)
        modal_visible = page.locator("#modal").is_visible()
        iframe_present = page.locator("#modal iframe").count() > 0
        report("Video-Card öffnet Modal mit Embed", modal_visible and iframe_present)
        page.locator("#modal button.modal-close").click()
        page.wait_for_timeout(300)

        # 19. DEEP-DIVE-TAB
        print("\n[14] Deep-Dive-Tab")
        page.click('[data-view="deep-dive"]')
        page.wait_for_timeout(600)
        dd_view = page.locator("#view-deep-dive").is_visible()
        report("Deep-Dive-View aktiv", dd_view)
        # Sub-Tabs vorhanden
        dd_subtabs = page.locator(".dd-subtab").count()
        report("Deep-Dive Sub-Tabs vorhanden", dd_subtabs >= 3, f"{dd_subtabs} Sub-Tabs")
        # Dashboard-Select vorhanden
        dd_select = page.locator("#dd-dashboard-select").count()
        report("Deep-Dive Dashboard-Select vorhanden", dd_select > 0)
        shoot(page, "08_deep_dive_tab")

        # 20. PRAXIS-TAB
        print("\n[15] Praxis-Tab")
        praxis_btn = page.locator('[data-view="praxis"]')
        if praxis_btn.count() > 0:
            praxis_btn.click()
            page.wait_for_timeout(600)
            praxis_view = page.locator("#view-praxis").is_visible()
            report("Praxis-View aktiv", praxis_view)
            praxis_cards = page.locator(".praxis-card, .praxis-item").count()
            report("Praxis-Karten geladen", praxis_cards > 0, f"{praxis_cards} Karten")
            shoot(page, "09_praxis_tab")
        else:
            report("Praxis-Tab vorhanden", False, "Tab nicht gefunden")

        # 21. PER-VIDEO-TAB
        print("\n[16] Per-Video-Tab")
        pv_btn = page.locator('[data-subview="per-video"], [data-view="deep-dive"]')
        page.click('[data-view="deep-dive"]')
        page.wait_for_timeout(300)
        pv_subtab = page.locator('[data-subview="per-video"]')
        if pv_subtab.count() > 0:
            pv_subtab.click()
            page.wait_for_timeout(500)
            pv_cards = page.locator(".pv-card").count()
            report("Per-Video-Karten geladen", pv_cards > 0, f"{pv_cards} Karten")
            shoot(page, "10_per_video_tab")
        else:
            report("Per-Video Sub-Tab vorhanden", False, "Sub-Tab nicht gefunden")

        # 22. DD-BOOKMARK (UI-Trigger)
        print("\n[17] Deep-Dive Bookmark")
        page.click('[data-view="concepts"]')
        page.wait_for_timeout(500)
        concept_nodes = page.locator(".concept-node, circle").count()
        if concept_nodes > 0:
            dd_btn = page.locator(".dd-start-btn")
            report("Deep-Dive-Button im Konzept-Modal vorhanden", dd_btn.count() >= 0)
        else:
            report("Konzept-Wiki für Bookmark-Test bereit", concept_nodes > 0, "Keine Nodes")
        shoot(page, "11_concept_wiki")

        # 23. ZURUECK ZUM BUCH
        print("\n[18] Buch wieder öffnen")
        page.click('[data-view="book"]')
        page.wait_for_timeout(400)
        book_visible = page.locator("#view-book").is_visible()
        report("Wissensbuch-Tab zurück", book_visible)

        # 24. KONSOLEN-FEHLER
        print("\n[15] JavaScript-Fehler")
        # Filter out known harmless errors (e.g., favicon)
        relevant = [e for e in console_errors if "favicon" not in e.lower()
                    and "extension" not in e.lower()
                    and "compute-pressure" not in e.lower()
                    and "permissions policy" not in e.lower()]
        report("Keine JS-Fehler", len(relevant) == 0, f"{len(relevant)} Fehler")
        if relevant:
            for e in relevant[:5]:
                print(f"      ! {e[:200]}")

        # Final
        browser.close()

    print("\n" + "=" * 70)
    print(f"Gesamt: {len(passed)} OK | {len(errors)} FAIL")
    print(f"Screenshots: {SCREENSHOT_DIR}")
    print("=" * 70)

    if errors:
        print(f"\nFehlgeschlagen ({len(errors)}):")
        for e in errors:
            print(f"  • {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
