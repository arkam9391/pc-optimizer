"""PC Optimizer: skany tylko odczytują dane. Narzędzia systemowe uruchamiane są wyłącznie na żądanie użytkownika."""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

from PySide6.QtCore import QPointF, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget,
                               QTabWidget, QVBoxLayout, QWidget)

import admin
import disks
import drivers
import recommend
import scanners as sc
import tuning
import updater
from version import __version__
from ui import (ACCENT, DOT, ICON, ICON_DIM, INK2, INK3, PAGE, SEG_COLORS, SEG_FREE, SEG_REST, SEG_USED, STYLE, THEME, THEMES,
                MetricCard, Page, SegBar, Worker, app_icon, fill, fit_height, glyph_icon, make_palette, make_table, marker_legend,
                save_theme, tool_button)

gb = sc.gb


def launch(what):
    """Uruchamia narzędzie Windows. what: lista (program + argumenty) albo URI/ścieżka."""
    try:
        if isinstance(what, (list, tuple)):
            subprocess.Popen(list(what))
        else:
            os.startfile(what)
    except OSError as e:
        print("Nie udało się uruchomić:", what, e)


def clear_layout(lay):
    while lay.count():
        w = lay.takeAt(0).widget()
        if w:
            w.deleteLater()


def box(title=None):
    f = QFrame(); f.setObjectName("box"); l = QVBoxLayout(f); l.setContentsMargins(16, 12, 16, 12); l.setSpacing(8)
    if title:
        t = QLabel(title); t.setStyleSheet("font-weight:500"); l.addWidget(t)
    return f, l


# ---------------------------------------------------------------- Przegląd
class OverviewPage(Page):
    def __init__(self, win):
        super().__init__("Przegląd", "Stan komputera i podsumowanie skanów", sc.scan_overview, button="Skanuj wszystko")
        self.win, self.actions = win, None

    def run(self):
        super().run()
        self.actions = None; self.draw_actions()
        self._rw = Worker(lambda: recommend.build_actions(recommend.measure()))
        self._rw.done.connect(self.on_actions); self._rw.start()
        for _, p in self.win.pages[1:]:
            if p is not self and not isinstance(p, (DisksPage, AdminPage)):
                p.run()

    def build(self):
        area = QScrollArea(); area.setWidgetResizable(True); area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setStyleSheet(f"QScrollArea {{ background: {PAGE}; border: none; }}")
        inner = QWidget(); inner.setObjectName("content"); il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 12, 0); il.setSpacing(12); area.setWidget(inner); self.body.addWidget(area, 1)
        row = QHBoxLayout(); row.setSpacing(12)
        self.c_ram, self.c_disk = MetricCard("RAM"), MetricCard("Dysk systemowy")
        self.c_auto, self.c_junk = MetricCard("Autostart", False), MetricCard("Do odzyskania", False)
        for c in (self.c_ram, self.c_disk, self.c_auto, self.c_junk):
            row.addWidget(c, 1)
        il.addLayout(row)
        f, fl = box("Zajętość dysku systemowego")
        self.seg = SegBar(); fl.addWidget(self.seg); il.addWidget(f)
        self.abox, al = box(); head = QHBoxLayout()
        t = QLabel("Zalecane akcje dla dysku C:"); t.setStyleSheet("font-weight:500")
        self.a_total = QLabel(""); self.a_total.setStyleSheet(f"font-family:Consolas;color:{INK2}")
        head.addWidget(t, 1); head.addWidget(self.a_total); al.addLayout(head)
        self.a_sub = QLabel(""); self.a_sub.setObjectName("muted"); self.a_sub.setWordWrap(True); al.addWidget(self.a_sub)
        self.a_rows = QVBoxLayout(); self.a_rows.setSpacing(0); al.addLayout(self.a_rows)
        al.addWidget(marker_legend()); il.addWidget(self.abox)
        self.fbox, self.find = box(); self.find.setSpacing(0); self.find.setContentsMargins(16, 4, 16, 4)
        il.addWidget(self.fbox)
        self.tbl = make_table(["Proces", "RAM"], num_cols=(1,)); il.addWidget(self.tbl)
        il.addStretch(1)

    def on_actions(self, res):
        self.actions = res; self.draw_actions()

    def draw_actions(self):
        if not self.built:
            return
        clear_layout(self.a_rows)
        a = self.actions
        if a is None or (isinstance(a, dict) and "__error__" in a):
            self.a_total.setText(""); self.a_sub.setText("")
            msg = "Liczę, ile miejsca można odzyskać…" if a is None else "Nie udało się obliczyć zaleceń: " + a["__error__"]
            lbl = QLabel(msg); lbl.setObjectName("muted"); self.a_rows.addWidget(lbl); return
        total = sum(r["gain"] or 0 for r in a)
        s = getattr(self, "sys_disk", None)
        self.a_total.setText(f"do odzyskania ok. {gb(total)}")
        if s:
            self.a_sub.setText(f"Wolne teraz {gb(s['free'])} z {gb(s['total'])}. Po pierwszych akcjach ok. {gb(s['free'] + total)}. "
                               "Rozmiary są szacunkiem, niektóre foldery systemowe są widoczne w pełni dopiero po uprawnieniach administratora")
        for r in a:
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 10, 0, 10); h.setSpacing(12)
            color, filled, _ = DOT[r["level"]]
            d = QLabel("●" if filled else "○"); d.setStyleSheet(f"color:{color};font-size:16px"); d.setFixedWidth(16)
            v = QVBoxLayout(); v.setSpacing(0)
            sub = QLabel(r["sub"]); sub.setObjectName("muted"); sub.setWordWrap(True)
            v.addWidget(QLabel(r["title"])); v.addWidget(sub)
            g = QLabel(gb(r["gain"]) if r["gain"] else "—"); g.setFixedWidth(88); g.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            g.setStyleSheet(f"font-family:Consolas;color:{INK2}")
            b = tool_button("Uruchom" if r["changes"] else "Otwórz", r["changes"]); b.setFixedWidth(120)
            b.clicked.connect(lambda _, k=r["key"]: self.act(k))
            h.addWidget(d); h.addLayout(v, 1); h.addWidget(g); h.addWidget(b)
            self.a_rows.addWidget(w)

    def act(self, key):
        w = self.win
        if key == "hiber":
            hiber_off(w)
        elif key == "dism":
            run_dism(w)
        elif key == "analyze":
            w.goto(DisksPage, run=True)
        else:
            launch({"cleanmgr": ["cleanmgr", "/dC"], "bin": ["explorer", "shell:RecycleBinFolder"],
                    "apps": "ms-settings:appsfeatures", "storage": "ms-settings:storagesense",
                    "downloads": ["explorer", os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")]}[key])

    def render(self, d):
        self.c_ram.set(f"{d['ram_percent']:.0f}%", f"wolne {gb(d['ram_free'])} z {gb(d['ram_total'])}", d["ram_percent"])
        s = next((x for x in d["disks"] if x["drive"].upper().startswith("C")), d["disks"][0])
        self.c_disk.set(f"{s['percent']:.0f}%", f"{s['drive']} wolne {gb(s['free'])} z {gb(s['total'])}", s["percent"])
        self.sys_disk = s
        self.set_segments(None)
        fill(self.tbl, [(n, gb(b)) for n, b in d["top_ram"]], (360, 0))
        fit_height(self.tbl)
        self.draw_actions()
        self.win.refresh_findings()
        return "Przegląd gotowy"

    def set_segments(self, folders):
        """folders: lista (nazwa, rozmiar) największych folderów C:, jeśli skan dysków już się odbył."""
        s = getattr(self, "sys_disk", None)
        if not s or not self.built:
            return
        segs, rest = [], s["total"] - s["free"]
        if folders:
            cols = SEG_COLORS
            for (name, size), c in zip(folders[:4], cols):
                segs.append((name, size, c)); rest -= size
            segs.append(("Inne", max(rest, 0), SEG_REST))
        else:
            segs.append(("Zajęte", rest, SEG_USED))
        segs.append(("Wolne", s["free"], SEG_FREE))
        self.seg.set(segs)

    def refresh(self, findings, autostart_n, junk):
        if not self.built:
            return
        self.c_auto.set(str(autostart_n) if autostart_n is not None else "—", "pozycji")
        self.c_junk.set(gb(junk) if junk is not None else "—", "tymczasowe i cache")
        clear_layout(self.find)
        for title, sub, val, key in findings:
            r = QWidget(); h = QHBoxLayout(r); h.setContentsMargins(0, 12, 0, 12); h.setSpacing(12)
            color, filled, _ = DOT[key]
            d = QLabel("●" if filled else "○"); d.setStyleSheet(f"color:{color};font-size:16px"); d.setFixedWidth(16)
            v = QVBoxLayout(); v.setSpacing(0)
            b = QLabel(sub); b.setObjectName("muted"); v.addWidget(QLabel(title)); v.addWidget(b)
            n = QLabel(val); n.setStyleSheet(f"font-family:Consolas;color:{INK2}")
            h.addWidget(d); h.addLayout(v, 1); h.addWidget(n)
            self.find.addWidget(r)


# ---------------------------------------------------------------- Sterowniki
class DriversPage(Page):
    LABEL = {"newer": ("Nowszy dostępny", "warn"), "ok": ("Aktualny", "ok"), "unknown": ("Nie sprawdzono", "gray")}

    def __init__(self):
        super().__init__("Sterowniki", "Wersje zainstalowane i najnowsze w katalogu Microsoft Update",
                         drivers.scan_drivers, True, "Szukaj aktualizacji")
        self.filter = "all"

    def build(self):
        row = QHBoxLayout(); row.setSpacing(8); self.chips = {}
        grp = QButtonGroup(self)
        for key, text in (("all", "Wszystkie"), ("newer", "Do aktualizacji"), ("ok", "Aktualne"), ("unknown", "Nie sprawdzono")):
            b = QPushButton(text); b.setObjectName("chip"); b.setCheckable(True); grp.addButton(b)
            b.clicked.connect(lambda _, k=key: self.set_filter(k)); self.chips[key] = b; row.addWidget(b)
        self.chips["all"].setChecked(True); row.addStretch(1); self.body.addLayout(row)
        self.tbl = make_table(["Status", "Urządzenie", "Za co odpowiada", "Wersja", "Data"], pill_cols=(0,), mono_cols=(3, 4))
        self.tbl.itemSelectionChanged.connect(self.show_detail)
        self.body.addWidget(self.tbl, 3)
        self.det, dl = box(); self.d_title = QLabel("Zaznacz sterownik, aby zobaczyć opis"); self.d_title.setStyleSheet("font-weight:500;font-size:14px")
        self.d_desc = QLabel(""); self.d_desc.setWordWrap(True)
        self.d_meta = QLabel(""); self.d_meta.setObjectName("muted"); self.d_meta.setWordWrap(True)
        dl.addWidget(self.d_title); dl.addWidget(self.d_desc); dl.addWidget(self.d_meta)
        br = QHBoxLayout(); br.setSpacing(8)
        self.b_vendor = tool_button("Strona producenta"); self.b_cat = tool_button("Katalog Microsoft")
        self.b_vendor.clicked.connect(lambda: self.cur and self.cur["link"] and QDesktopServices.openUrl(QUrl(self.cur["link"])))
        self.b_cat.clicked.connect(lambda: self.cur and self.cur["catalog"] and QDesktopServices.openUrl(QUrl(self.cur["catalog"])))
        br.addWidget(self.b_vendor); br.addWidget(self.b_cat); br.addStretch(1); dl.addLayout(br)
        self.body.addWidget(self.det)
        n = QLabel("Wersje z katalogu Microsoft mogą być starsze od tych na stronie producenta. Przed instalacją utwórz punkt przywracania. "
                   "Aplikacja niczego nie instaluje."); n.setObjectName("muted"); n.setWordWrap(True)
        self.body.addWidget(n)
        self.cur = None; self.rows = []

    def set_filter(self, k):
        self.filter = k; self.fill_table()

    def fill_table(self):
        self.rows = [d for d in self.data if self.filter == "all" or d["status"] == self.filter]
        fill(self.tbl, [(self.LABEL[d["status"]], d["name"], d["desc"],
                         f"{d['version']}  →  {d['latest']['version']}" if d["status"] == "newer" and d["latest"] else d["version"],
                         d["date"]) for d in self.rows], (150, 200, 230, 270, 0))

    def show_detail(self):
        r = self.tbl.currentRow()
        if r < 0 or r >= len(self.rows):
            return
        d = self.cur = self.rows[r]
        self.d_title.setText(d["name"]); self.d_desc.setText(d["desc"])
        lat = f" · najnowsza w katalogu: {d['latest']['version']} z {d['latest']['date']}" if d["latest"] else ""
        self.d_meta.setText(f"{d['note']} · zainstalowana: {d['version']} z {d['date']}{lat} · dostawca: {d['provider'] or '?'}")
        self.b_vendor.setEnabled(bool(d["link"])); self.b_cat.setEnabled(bool(d["catalog"]))

    def render(self, data):
        self.fill_table()
        n = sum(d["status"] == "newer" for d in data)
        for k, t in (("all", f"Wszystkie ({len(data)})"), ("newer", f"Do aktualizacji ({n})"),
                     ("ok", f"Aktualne ({sum(d['status'] == 'ok' for d in data)})"),
                     ("unknown", f"Nie sprawdzono ({sum(d['status'] == 'unknown' for d in data)})")):
            self.chips[k].setText(t)
        return f"Sterowników: {len(data)}, z nowszą wersją: {n}"


# ---------------------------------------------------------------- Dane techniczne
class HardwarePage(Page):
    def __init__(self):
        super().__init__("Dane techniczne", "Specyfikacja podzespołów", sc.scan_hardware, button="Odczytaj dane")
        b = QPushButton("Eksportuj raport"); b.clicked.connect(self.export); self.actions.insertWidget(0, b)

    def build(self):
        self.tabs = QTabWidget(); self.body.addWidget(self.tabs)

    def render(self, hw):
        self.tabs.clear()
        for name, rows in hw.items():
            t = make_table(["Parametr", "Wartość"], mono_cols=(1,)); fill(t, rows, (280, 0)); self.tabs.addTab(t, name)
        return "Odczytano dane techniczne"

    def export(self):
        if not self.data:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz raport", "dane_techniczne.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- Narzędzia i potwierdzenia
TOOLS = [  # nazwa, opis, klucz, czy zmienia system
    ("Oczyszczanie dysku", "Usuwa pliki tymczasowe, kosz, miniatury i cache Windows Update", "cleanmgr", True),
    ("Optymalizuj dyski", "Defragmentacja HDD i TRIM dla SSD", "dfrgui", True),
    ("Czyszczenie składników Windows", "DISM: usuwa zbędne składniki WinSxS (wymaga administratora)", "dism", True),
    ("Czujnik pamięci", "Automatyczne zwalnianie miejsca w ustawieniach Windows", "storage", False),
    ("Aplikacje i funkcje", "Odinstalowanie dużych, nieużywanych programów", "apps", False),
    ("Kosz", "Przejrzyj i opróżnij kosz", "bin", False),
    ("Zarządzanie dyskami", "Partycje, litery dysków, rozmiary", "diskmgmt", False),
]

DISM_SCRIPT = ("Write-Host 'Analiza magazynu składników...' -ForegroundColor Cyan; "
               "dism /Online /Cleanup-Image /AnalyzeComponentStore; "
               "Write-Host ''; Write-Host 'Czyszczenie składników (StartComponentCleanup)...' -ForegroundColor Cyan; "
               "dism /Online /Cleanup-Image /StartComponentCleanup; "
               "Write-Host ''; Write-Host 'Gotowe. Możesz zamknąć to okno.' -ForegroundColor Green")


def run_dism(parent):
    ok = QMessageBox.question(
        parent, "Czyszczenie składników Windows",
        "Zostanie uruchomione okno PowerShell jako administrator (potwierdzisz je w UAC), a w nim:\n\n"
        "1. dism /Online /Cleanup-Image /AnalyzeComponentStore\n"
        "2. dism /Online /Cleanup-Image /StartComponentCleanup\n\n"
        "Usuwa tylko zastąpione składniki Windows. Nie używa /ResetBase, więc aktualizacje nadal można odinstalować. "
        "Operacja może potrwać kilkanaście minut.\n\nUruchomić?") == QMessageBox.Yes
    if ok:
        admin.run_elevated(DISM_SCRIPT, visible=True, keep_open=True)


def confirm_elevated(parent, title, text, script, keep_open=False):
    """Pokazuje opis zmiany i dopiero po potwierdzeniu uruchamia skrypt z uprawnieniami administratora."""
    if QMessageBox.question(parent, title, text + "\n\nUruchomić? (zostaniesz poproszony o potwierdzenie w UAC)") == QMessageBox.Yes:
        admin.run_elevated(script, visible=True, keep_open=keep_open)


def confirm_restart(parent):
    if QMessageBox.question(parent, "Uruchom ponownie",
                            "Komputer zostanie uruchomiony ponownie za 30 sekund. Zapisz otwartą pracę.\n"
                            "Możesz to anulować poleceniem: shutdown /a\n\nKontynuować?") == QMessageBox.Yes:
        launch(["shutdown", "/r", "/t", "30", "/c", "PC Optimizer: restart na Twoje żądanie"])


HIBER_OFF = ("powercfg /h off; Write-Host 'Hibernacja i szybki start wyłączone. Cofniesz poleceniem: powercfg /h on' -ForegroundColor Green; "
             "Start-Sleep 6")


def hiber_off(parent):
    confirm_elevated(parent, "Wyłączenie hibernacji",
                     "Wykona polecenie: powercfg /h off\nUsuwa plik hiberfil.sys (zwalnia miejsce na C:) i wyłącza szybki start. "
                     "Na laptopie tracisz hibernację. Cofniesz poleceniem: powercfg /h on", HIBER_OFF)


class OptimizePage(Page):
    LABEL = {"ok": "OK", "warn": "Do poprawy", "bad": "Uwaga", "info": "Opcjonalnie"}

    def __init__(self):
        super().__init__("Optymalizacja", "Ustawienia wpływające na szybkość. Każda zmiana wymaga Twojego potwierdzenia",
                         tuning.scan_tuning, button="Sprawdź ustawienia")

    def build(self):
        self.tbl = make_table(["Ocena", "Element", "Stan", "Zalecenie"], pill_cols=(0,), mono_cols=(2,)); self.body.addWidget(self.tbl)
        f, bl = box("Działania")
        acts = [
            ("Uruchom ponownie", True, lambda: confirm_restart(self)),
            ("Wyłącz hibernację", True, lambda: hiber_off(self)),
            ("Plik wymiany i efekty wizualne", False, lambda: launch(["SystemPropertiesPerformance.exe"])),
            ("Autostart", False, lambda: launch("ms-settings:startupapps")),
            ("Plan zasilania", False, lambda: launch(["control", "powercfg.cpl"])),
            ("Odinstaluj programy", False, lambda: launch("ms-settings:appsfeatures")),
        ]
        grid = QGridLayout(); grid.setSpacing(0)
        for i, (name, ch, fn) in enumerate(acts):
            b = tool_button(name, ch); b.clicked.connect(lambda _, f=fn: f()); grid.addWidget(b, i // 3, i % 3)
        bl.addLayout(grid)
        h = QLabel("Plik wymiany: w oknie Opcje wydajności wybierz Zaawansowane → Pamięć wirtualna → Zmień. "
                   "Ustaw rozmiar niestandardowy na C: (przy 32 GB RAM wystarczy 2048–4096 MB) i usuń plik z E:."); h.setObjectName("muted"); h.setWordWrap(True)
        bl.addWidget(h); bl.addWidget(marker_legend())
        self.body.addWidget(f); self.body.addStretch(1)

    def render(self, rows):
        order = {"bad": 0, "warn": 1, "info": 2, "ok": 3}
        rows = sorted(rows, key=lambda r: order[r[0]])
        fill(self.tbl, [((self.LABEL[k], k), n, s, z) for k, n, s, z in rows], (150, 200, 280, 0))
        fit_height(self.tbl)
        return f"Do poprawy: {sum(r[0] in ('warn', 'bad') for r in rows)} z {len(rows)}"


class AdminPage(Page):
    def __init__(self):
        super().__init__("Analiza administratora", "Dane dostępne tylko z uprawnieniami administratora, wyłącznie odczyt",
                         admin.scan_admin, True, "Uruchom analizę")

    def build(self):
        self.tabs = QTabWidget(); self.body.addWidget(self.tabs, 1)
        n = QLabel("Po kliknięciu pojawi się okno UAC. Skrypt odczytuje SMART, punkty przywracania, wyjątki Defendera, czas startu i hibernację. "
                   "Niczego nie zmienia. Analiza WinSxS (DISM) jest wolna, więc działa osobno w zakładce Dyski."); n.setObjectName("muted"); n.setWordWrap(True)
        self.body.addWidget(n)

    @staticmethod
    def _text(s):
        w = QPlainTextEdit(); w.setReadOnly(True); w.setPlainText((s or "").strip() or "Brak danych")
        w.setStyleSheet("font-family: Consolas; font-size: 12px;"); return w

    def render(self, d):
        self.tabs.clear()
        def lst(x):
            return x if isinstance(x, list) else ([x] if x else [])
        t = make_table(["Dysk", "Typ", "Zdrowie", "Temp. °C", "Zużycie SSD %", "Błędy odczytu", "Błędy zapisu", "Godziny pracy"],
                       num_cols=(3, 4, 5, 6, 7))
        def v(x, k):  # dysk bez liczników niezawodności zwraca zera i nulle: pokazujemy "—" zamiast mylących wartości
            ok = x.get("Hours") is not None
            val = x.get(k)
            return "—" if (not ok and k in ("Temp", "Wear")) or val is None else val
        fill(t, [(x["Name"], x["Media"], x["Health"], v(x, "Temp"), v(x, "Wear"), v(x, "ReadErr"), v(x, "WriteErr"), v(x, "Hours"))
                 for x in lst(d.get("disks"))])
        self.tabs.addTab(t, "Dyski (SMART)")
        sm = lst(d.get("smart"))
        self.tabs.addTab(self._text("\n".join(f"{x['Instance']}: {'PRZEWIDYWANA AWARIA' if x['PredictFailure'] else 'brak ostrzeżeń'}" for x in sm)),
                         "Przewidywanie awarii")
        self.tabs.addTab(self._text(d.get("shadow")), "Punkty przywracania")
        self.tabs.addTab(self._text("\n".join(lst(d.get("exclusions"))) or "Brak wyjątków"), "Wyjątki Defendera")
        b = make_table(["Data", "Start (s)", "Główna faza (s)", "Po starcie (s)"], num_cols=(1, 2, 3))
        fill(b, [(x["Time"], x["BootSec"], x["MainPathSec"], x["PostBootSec"]) for x in lst(d.get("boot"))])
        self.tabs.addTab(b, "Czas startu")
        self.tabs.addTab(self._text(d.get("hiber")), "Hibernacja")
        return "Analiza zakończona"


# ---------------------------------------------------------------- Dyski
class DisksPage(Page):
    def __init__(self, win=None):
        super().__init__("Dyski", "Zajętość, największe foldery i pliki oraz narzędzia do zwalniania miejsca",
                         disks.scan_drives, button="Skanuj dyski")
        self.win, self.sel, self.path, self.fw, self.hist = win, None, None, None, []

    def build(self):
        self.chiprow = QHBoxLayout(); self.chiprow.setSpacing(8); self.body.addLayout(self.chiprow)
        f, fl = box(); self.cap = QLabel(""); self.cap.setObjectName("cap"); fl.addWidget(self.cap)
        self.seg = SegBar(); fl.addWidget(self.seg); self.body.addWidget(f)
        nav = QHBoxLayout(); nav.setSpacing(8)
        self.crumb = QLabel(""); self.crumb.setObjectName("sub")
        self.b_up = QPushButton("W górę"); self.b_up.clicked.connect(self.go_up)
        self.b_exp = QPushButton("Otwórz w Eksploratorze"); self.b_exp.clicked.connect(lambda: self.path and launch(["explorer", self.path]))
        nav.addWidget(self.crumb, 1); nav.addWidget(self.b_up); nav.addWidget(self.b_exp); self.body.addLayout(nav)
        self.tbl = make_table(["Nazwa", "Rozmiar", "Udział"], bar_cols=(2,), num_cols=(1,))
        self.tbl.cellDoubleClicked.connect(self.enter)
        self.body.addWidget(self.tbl, 4)
        l = QLabel("Duże pliki (od 300 MB) w bieżącym folderze. Dwuklik pokazuje plik w Eksploratorze"); l.setObjectName("muted"); self.body.addWidget(l)
        self.big = make_table(["Plik", "Rozmiar"], mono_cols=(0,), num_cols=(1,)); self.big.cellDoubleClicked.connect(
            lambda r, c: launch(["explorer", "/select,", self.big.item(r, 0).text()]))
        self.big.setMinimumHeight(76); self.body.addWidget(self.big, 1)
        f2, bl = box("Narzędzia")
        self.hint = QLabel(""); self.hint.setObjectName("muted"); self.hint.setWordWrap(True); bl.addWidget(self.hint)
        grid = QGridLayout(); grid.setSpacing(0)
        for i, (name, desc, key, ch) in enumerate(TOOLS):
            b = tool_button(name, ch, desc); b.clicked.connect(lambda _, k=key: self.tool(k)); grid.addWidget(b, i // 4, i % 4)
        bl.addLayout(grid); bl.addWidget(marker_legend()); self.body.addWidget(f2)

    def tool(self, key):
        if key == "dism":
            return run_dism(self)
        letter = self.sel["letter"] if self.sel else "C"
        launch({"cleanmgr": ["cleanmgr", f"/d{letter}"], "storage": "ms-settings:storagesense", "dfrgui": ["dfrgui"],
                "apps": "ms-settings:appsfeatures", "bin": ["explorer", "shell:RecycleBinFolder"],
                "diskmgmt": ["mmc", "diskmgmt.msc"]}[key])

    def render(self, drives):
        clear_layout(self.chiprow)
        self.btns = []
        grp = QButtonGroup(self)
        for d in drives:
            b = QPushButton(f"{d['letter']}:  {d['media']}  {gb(d['total'])}"); b.setObjectName("chip"); b.setCheckable(True); grp.addButton(b)
            b.clicked.connect(lambda _, x=d: self.select(x)); self.chiprow.addWidget(b); self.btns.append(b)
        self.chiprow.addStretch(1)
        start = next((i for i, d in enumerate(drives) if d["letter"] == "C"), 0)
        self.btns[start].setChecked(True); self.select(drives[start])
        return f"Dysków: {len(drives)}"

    def select(self, d):
        self.sel, self.hist = d, []
        self.cap.setText(f"Dysk {d['letter']}:  {d['model']} ({d['media']}) · stan: {d['health']} · {d['percent']:.0f}% zajęte")
        used = d["total"] - d["free"]
        self.seg.set([("Zajęte", used, SEG_USED), ("Wolne", d["free"], SEG_FREE)])
        if d["media"] == "HDD":
            self.hint.setText("Dysk HDD: pomaga defragmentacja (Optymalizuj dyski) i Oczyszczanie dysku")
        else:
            self.hint.setText("Dysk SSD: nie defragmentuj, wystarczy TRIM (Optymalizuj dyski). Miejsce zwolnisz przez Oczyszczanie dysku i Czujnik pamięci")
        self.scan_dir(d["mount"])

    def scan_dir(self, path):
        self.path = path
        self.crumb.setText(f"Skanuję {path}"); self.busy.show()
        self.fw = Worker(lambda: disks.scan_folder(path)); self.fw.done.connect(self.show_dir); self.fw.start()

    def show_dir(self, r):
        self.busy.hide()
        if "__error__" in r or r.get("error"):
            self.crumb.setText("Brak dostępu: " + (r.get("error") or r["__error__"])); return
        self.crumb.setText(f"{r['path']}  ·  razem {gb(r['total'])}")
        top = max((i["size"] for i in r["items"]), default=1) or 1
        self.items = r["items"]
        d_icon, f_icon = glyph_icon("", ICON, 28), glyph_icon("", ICON_DIM, 28)
        fill(self.tbl, [(i["name"], gb(i["size"]), ("", None, i["size"] / top)) for i in r["items"]], (440, 110, 0),
             icons={n: (d_icon if i["is_dir"] else f_icon) for n, i in enumerate(r["items"])})
        fill(self.big, [(p, gb(s)) for p, s in r["big"]], (680, 0))
        self.b_up.setEnabled(bool(self.hist))
        if self.sel and r["path"] == self.sel["mount"]:  # pasek zajętości dzieli dysk na największe foldery
            folders = [(i["name"], i["size"]) for i in r["items"] if i["is_dir"]][:4]
            used = self.sel["total"] - self.sel["free"]; rest = used - sum(s for _, s in folders)
            cols = SEG_COLORS
            segs = [(n, s, c) for (n, s), c in zip(folders, cols)] + [("Inne", max(rest, 0), SEG_REST), ("Wolne", self.sel["free"], SEG_FREE)]
            self.seg.set(segs)
            if self.win and self.sel["letter"] == "C":
                self.win.over.set_segments(folders)
        self.status.setText(f"Przeskanowano {r['path']}  ·  {datetime.now():%H:%M:%S}")

    def enter(self, row, _):
        it = self.items[row]
        if it["is_dir"]:
            self.hist.append(self.path); self.scan_dir(it["path"])

    def go_up(self):
        if self.hist:
            self.scan_dir(self.hist.pop())


# ---------------------------------------------------------------- Pozostałe
class JunkPage(Page):
    def __init__(self):
        super().__init__("Pliki zbędne", "Pliki tymczasowe, cache przeglądarek i Windows Update", sc.scan_junk)
        b = QPushButton("Oczyszczanie dysku"); b.clicked.connect(lambda: launch(["cleanmgr", "/dC"]))
        c = QPushButton("Czujnik pamięci"); c.clicked.connect(lambda: launch("ms-settings:storagesense"))
        self.actions.insertWidget(0, c); self.actions.insertWidget(0, b)

    def build(self):
        self.tbl = make_table(["Kategoria", "Rozmiar", "Udział", "Ścieżka"], bar_cols=(2,), num_cols=(1,))
        self.body.addWidget(self.tbl); self.body.addStretch(1)

    def render(self, d):
        top = max((x["size"] for x in d), default=1) or 1
        fill(self.tbl, [(x["name"], gb(x["size"]), ("", None, x["size"] / top), x["path"]) for x in d], (220, 110, 200, 0))
        fit_height(self.tbl)
        return f"Do odzyskania: {gb(sum(x['size'] for x in d))}. Nic nie zostało usunięte"


class StartupPage(Page):
    KEY = {"Duży": "bad", "Średni": "warn", "Mały": "gray"}

    def __init__(self):
        super().__init__("Autostart", "Programy uruchamiane razem z systemem. Podgląd, bez zmian", sc.scan_startup)
        b = QPushButton("Zarządzaj w Windows"); b.clicked.connect(lambda: launch("ms-settings:startupapps")); self.actions.insertWidget(0, b)

    def build(self):
        self.tbl = make_table(["Wpływ", "Nazwa", "Źródło", "Polecenie"], pill_cols=(0,), mono_cols=(3,)); self.body.addWidget(self.tbl)

    def render(self, d):
        fill(self.tbl, [((x["impact"], self.KEY[x["impact"]]), x["name"], x["source"], x["command"]) for x in d], (130, 220, 160, 0))
        return f"Pozycji: {len(d)}"


class ProgramsPage(Page):
    def __init__(self):
        super().__init__("Programy", "Zainstalowane aplikacje wg rozmiaru", sc.scan_programs)
        b = QPushButton("Aplikacje i funkcje"); b.clicked.connect(lambda: launch("ms-settings:appsfeatures")); self.actions.insertWidget(0, b)

    def build(self):
        self.tbl = make_table(["Nazwa", "Wersja", "Wydawca", "Data instalacji", "Rozmiar"], mono_cols=(1, 3), num_cols=(4,)); self.body.addWidget(self.tbl)

    def render(self, d):
        fill(self.tbl, [(x["name"], x["version"], x["publisher"], x["date"], gb(x["size"]) if x["size"] else "—") for x in d],
             (340, 130, 200, 130, 0))
        return f"Pozycji: {len(d)}"


# ---------------------------------------------------------------- Okno główne
class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PC Optimizer"); self.resize(1240, 800)
        self.over = OverviewPage(self)
        self.pages = [("Przegląd", "", self.over), ("Sterowniki", "", DriversPage()),
                      ("Dane techniczne", "", HardwarePage()), ("Dyski", "", DisksPage(self)),
                      ("Autostart", "", StartupPage()), ("Programy", "", ProgramsPage()),
                      ("Pliki zbędne", "", JunkPage()), ("Optymalizacja", "", OptimizePage()),
                      ("Analiza administratora", "", AdminPage())]
        icons = [i for _, i, _ in self.pages]
        self.pages = [(n, p) for n, _, p in self.pages]
        side = QFrame(); side.setObjectName("side"); side.setFixedWidth(240)
        sl = QVBoxLayout(side); sl.setContentsMargins(12, 16, 12, 12); sl.setSpacing(4)
        br = QLabel("PC Optimizer"); br.setObjectName("brand"); sl.addWidget(br)
        self.stack = QStackedWidget(); grp = QButtonGroup(self); self.navs = []
        for i, ((name, page), ic) in enumerate(zip(self.pages, icons)):
            b = QPushButton(name); b.setObjectName("nav"); b.setCheckable(True); b.setIcon(glyph_icon(ic)); b.setIconSize(QSize(16, 16))
            self.navs.append(b)
            b.clicked.connect(lambda _, i=i: self.stack.setCurrentIndex(i)); grp.addButton(b); sl.addWidget(b)
            self.stack.addWidget(page); page.scanned.connect(self.refresh_findings)
            if i == 0:
                b.setChecked(True)
        sl.addStretch(1)
        self.upd_btn = QPushButton(); self.upd_btn.setObjectName("nav"); self.upd_btn.hide()
        self.upd_btn.clicked.connect(self.install_update); sl.addWidget(self.upd_btn)
        cap = QLabel("Motyw"); cap.setObjectName("muted"); cap.setContentsMargins(12, 0, 0, 0); sl.addWidget(cap)
        self.theme_box = QComboBox()
        for key, t in THEMES.items():
            self.theme_box.addItem(t["label"], key)
        self.theme_box.setCurrentIndex(list(THEMES).index(THEME))
        self.theme_box.setStyleSheet(f"QComboBox::down-arrow {{ image: url({self.chevron()}); width: 12px; height: 12px; }}")
        self.theme_box.activated.connect(self.change_theme); sl.addWidget(self.theme_box)
        mode = QLabel(f"○  Skany tylko odczytują dane\n    Wersja {__version__}"); mode.setObjectName("muted")
        mode.setContentsMargins(12, 0, 0, 0); sl.addWidget(mode)
        self.update_info = None
        QTimer.singleShot(2000, self.check_update)
        root = QWidget(); root.setObjectName("root"); lay = QHBoxLayout(root); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
        lay.addWidget(side); lay.addWidget(self.stack, 1); self.setCentralWidget(root)

    def page(self, cls):
        return next(p for _, p in self.pages if isinstance(p, cls))

    @staticmethod
    def chevron():
        """Strzałka listy motywów w kolorze motywu; arkusz stylów potrzebuje pliku obrazu."""
        path = os.path.join(tempfile.gettempdir(), f"pcopt_chevron_{THEME}.png")
        pm = QPixmap(24, 24); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setPen(QPen(QColor(INK3), 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline([QPointF(6, 9), QPointF(12, 15), QPointF(18, 9)]); p.end()
        pm.save(path)
        return path.replace("\\", "/")

    def change_theme(self, i):
        key = self.theme_box.itemData(i)
        if key == THEME:
            return
        if QMessageBox.question(self, "Motyw", "Motyw zmieni się po ponownym uruchomieniu programu. Wyniki skanów zostaną wyczyszczone.\n\n"
                                "Uruchomić ponownie teraz?") != QMessageBox.Yes:
            self.theme_box.setCurrentIndex(list(THEMES).index(THEME)); return
        save_theme(key)
        cmd = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, os.path.abspath(sys.argv[0])]
        env = {k: v for k, v in os.environ.items() if k != "PCOPT_THEME"}
        subprocess.Popen(cmd, env=env)
        QApplication.quit()

    def goto(self, cls, run=False):
        i = next(i for i, (_, p) in enumerate(self.pages) if isinstance(p, cls))
        self.stack.setCurrentIndex(i); self.navs[i].setChecked(True)
        if run and self.pages[i][1].data is None:
            self.pages[i][1].run()

    # Aktualizacje: sprawdzenie w tle po starcie; instalacja dopiero po potwierdzeniu
    def check_update(self):
        self._uw = Worker(updater.check_update)
        self._uw.done.connect(self.on_update_checked); self._uw.start()

    def on_update_checked(self, info):
        if not info or "__error__" in info:
            return
        self.update_info = info
        self.upd_btn.setText(f"●  Dostępna wersja {info['version']}"); self.upd_btn.show()

    def install_update(self):
        info = self.update_info
        notes = info["notes"][:600] or "Brak opisu zmian."
        if QMessageBox.question(self, "Aktualizacja", f"Pobrać i zainstalować wersję {info['version']}?\n\n{notes}\n\n"
                                "Program zamknie się i uruchomi ponownie po instalacji.") != QMessageBox.Yes:
            return
        self.upd_btn.setEnabled(False)
        self._dw = Worker(lambda p: updater.download_installer(info, p), pass_progress=True)
        self._dw.msg.connect(lambda m: self.upd_btn.setText(m)); self._dw.done.connect(self.on_downloaded); self._dw.start()

    def on_downloaded(self, res):
        if isinstance(res, dict) and "__error__" in res:
            self.upd_btn.setEnabled(True); self.upd_btn.setText(f"●  Dostępna wersja {self.update_info['version']}")
            QMessageBox.warning(self, "Aktualizacja", res["__error__"]); return
        updater.run_installer(res)
        QApplication.quit()

    def refresh_findings(self):
        f, auto_n, junk = [], None, None
        d = self.page(DriversPage).data
        if d is not None:
            n = sum(x["status"] == "newer" for x in d)
            f.append(("Sterowniki", f"{n} z {len(d)} ma nowszą wersję w katalogu Microsoft", f"{n} do aktualizacji", "warn" if n else "ok"))
        a = self.page(StartupPage).data
        if a is not None:
            auto_n = len(a); h = sum(x["impact"] == "Duży" for x in a)
            f.append(("Autostart", f"{h} pozycji mocno wpływa na czas startu", f"{h} do przejrzenia", "warn" if h else "ok"))
        j = self.page(JunkPage).data
        if j is not None:
            junk = sum(x["size"] for x in j)
            f.append(("Pliki zbędne", "Pliki tymczasowe, cache i Windows Update", gb(junk), "info"))
        f.append(("Wsparcie Windows 10", "System poza standardowym wsparciem Microsoftu", "uwaga", "bad"))
        self.over.refresh(f, auto_n, junk)


if __name__ == "__main__":
    try:  # własny identyfikator, żeby pasek zadań pokazywał ikonę aplikacji, a nie Pythona
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PCOptimizer.App")
    except (AttributeError, OSError):
        pass
    app = QApplication(sys.argv)
    app.setStyle("Fusion"); app.setPalette(make_palette()); app.setStyleSheet(STYLE); app.setWindowIcon(app_icon())
    w = Main(); w.show()
    sys.exit(app.exec())
