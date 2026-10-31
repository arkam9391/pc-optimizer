"""Elementy interfejsu. Kierunek: grafit, jeden akcent (kobalt), liczby w mono, statusy jako kropki."""
from datetime import datetime

from PySide6.QtCore import QRectF, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QSizePolicy, QStyle, QStyledItemDelegate, QStyleOptionViewItem,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

# --- tokeny ---------------------------------------------------------------
INK, INK2, INK3 = "#171717", "#525252", "#737373"
LINE, PAGE, CARD, SIDE, RAISED = "#e6e6e8", "#fafafa", "#ffffff", "#f4f4f5", "#ececee"
ACCENT = "#2b59c3"
MONO = "Consolas"
DOT = {  # klucz: (kolor kropki, wypełniona?, kolor tekstu)
    "warn": ("#d97706", True, INK), "bad": ("#dc2626", True, INK), "ok": ("#16a34a", True, INK2),
    "info": ("#a1a1aa", False, INK2), "gray": ("#a1a1aa", False, INK3),
}
ROLE_KEY, ROLE_BAR = Qt.UserRole + 1, Qt.UserRole + 2

STYLE = f"""
* {{ font-family: "Segoe UI"; font-size: 13px; color: {INK}; }}
QMainWindow, #root, #content {{ background: {PAGE}; }}
#side {{ background: {SIDE}; border-right: 1px solid {LINE}; }}
#brand {{ font-size: 16px; font-weight: 500; padding: 4px 12px 16px 12px; }}
QPushButton#nav {{ text-align: left; padding: 8px 12px; border: none; border-radius: 8px; background: transparent; color: {INK2}; }}
QPushButton#nav:hover {{ background: {RAISED}; }}
QPushButton#nav:checked {{ background: #e4e4e7; color: {INK}; font-weight: 500; }}
QPushButton {{ padding: 8px 16px; border: 1px solid #d9d9dc; border-radius: 8px; background: {CARD}; }}
QPushButton:hover {{ background: {SIDE}; }}
QPushButton:pressed {{ background: {RAISED}; }}
QPushButton:disabled {{ color: #a1a1aa; background: {PAGE}; }}
QPushButton#primary {{ background: {INK}; color: #ffffff; border: none; }}
QPushButton#primary:hover {{ background: #333333; }}
QPushButton#primary:disabled {{ background: #a1a1aa; color: #ffffff; }}
QPushButton#chip {{ padding: 4px 12px; color: {INK2}; }}
QPushButton#chip:checked {{ background: #e4e4e7; color: {INK}; border-color: #c9c9ce; }}
QPushButton#tool {{ text-align: left; padding: 8px 12px; border: none; background: transparent; }}
QPushButton#tool:hover {{ background: {RAISED}; }}
QLabel#h {{ font-size: 24px; font-weight: 500; }}
QLabel#sub {{ color: {INK2}; }}
QLabel#muted {{ color: {INK3}; font-size: 12px; }}
QLabel#status {{ color: {INK3}; font-size: 12px; }}
QLabel#cap {{ color: {INK2}; font-size: 12px; }}
#card, #box {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 12px; }}
QLabel#metric {{ font-family: {MONO}; font-size: 26px; }}
QProgressBar {{ background: {LINE}; border: none; border-radius: 2px; max-height: 4px; min-height: 4px; }}
QProgressBar::chunk {{ background: #52525b; border-radius: 2px; }}
QProgressBar#busy {{ max-height: 2px; min-height: 2px; }}
QProgressBar#busy::chunk {{ background: {ACCENT}; }}
QTableWidget {{ border: 1px solid {LINE}; border-radius: 12px; gridline-color: transparent; background: {CARD};
  selection-background-color: {SIDE}; selection-color: {INK}; outline: 0; }}
QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid #f0f0f1; }}
QHeaderView::section {{ background: {CARD}; border: none; border-bottom: 1px solid {LINE}; padding: 8px; color: {INK3}; font-size: 12px; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ padding: 8px 12px; margin-right: 4px; border-radius: 8px; background: transparent; color: {INK2}; }}
QTabBar::tab:selected {{ background: #e4e4e7; color: {INK}; }}
QPlainTextEdit {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 12px; padding: 8px; }}
QScrollBar:vertical {{ width: 8px; background: transparent; margin: 4px 0; }}
QScrollBar::handle:vertical {{ background: #d4d4d8; border-radius: 4px; min-height: 32px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: #d4d4d8; border-radius: 4px; min-width: 32px; }}
"""


def glyph_icon(ch, color=INK3, px=30):
    pm = QPixmap(40, 40); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.TextAntialiasing)
    f = QFont("Segoe MDL2 Assets"); f.setPixelSize(px); p.setFont(f); p.setPen(QColor(color))
    p.drawText(pm.rect(), Qt.AlignCenter, ch); p.end()
    return QIcon(pm)


def mono(px=12):
    f = QFont(MONO); f.setPixelSize(px); return f


class StatusDelegate(QStyledItemDelegate):
    """Status jako mała kropka i tekst. Pełna kropka niesie sygnał, pusta oznacza brak pilności."""

    def paint(self, p, opt, idx):
        key = idx.data(ROLE_KEY)
        if key not in DOT:
            return super().paint(p, opt, idx)
        o = QStyleOptionViewItem(opt); self.initStyleOption(o, idx)
        text, o.text = o.text, ""
        (o.widget.style() if o.widget else QApplication.style()).drawControl(QStyle.CE_ItemViewItem, o, p, o.widget)
        color, filled, tcolor = DOT[key]
        p.save(); p.setRenderHint(QPainter.Antialiasing)
        c = QRectF(opt.rect.left() + 8, opt.rect.center().y() - 4, 8, 8)
        if filled:
            p.setPen(Qt.NoPen); p.setBrush(QColor(color))
        else:
            p.setPen(QColor(color)); p.setBrush(Qt.NoBrush); c.adjust(0.5, 0.5, -0.5, -0.5)
        p.drawEllipse(c)
        p.setPen(QColor(tcolor)); p.setFont(opt.font)
        p.drawText(QRectF(opt.rect.left() + 24, opt.rect.top(), opt.rect.width() - 28, opt.rect.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, QFontMetrics(opt.font).elidedText(text, Qt.ElideRight, opt.rect.width() - 28))
        p.restore()


class BarDelegate(QStyledItemDelegate):
    """Cienki pasek udziału. Najdłuższy pasek dostaje akcent, reszta jest neutralna."""

    def paint(self, p, opt, idx):
        frac = idx.data(ROLE_BAR)
        if frac is None:
            return super().paint(p, opt, idx)
        o = QStyleOptionViewItem(opt); self.initStyleOption(o, idx); o.text = ""
        (o.widget.style() if o.widget else QApplication.style()).drawControl(QStyle.CE_ItemViewItem, o, p, o.widget)
        r = QRectF(opt.rect.left() + 8, opt.rect.center().y() - 2, opt.rect.width() - 16, 4)
        p.save(); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
        p.setBrush(QColor(LINE)); p.drawRoundedRect(r, 2, 2)
        p.setBrush(QColor(ACCENT if frac >= 0.999 else "#a1a1aa"))
        p.drawRoundedRect(QRectF(r.left(), r.top(), max(3.0, r.width() * frac), 4), 2, 2)
        p.restore()


def make_table(headers, pill_cols=(), bar_cols=(), num_cols=(), mono_cols=()):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setShowGrid(False)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(36)
    t.horizontalHeader().setStretchLastSection(True)
    t.horizontalHeader().setHighlightSections(False)
    t.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    t.horizontalHeader().setFixedHeight(36)
    t.setFocusPolicy(Qt.NoFocus)
    t.setTextElideMode(Qt.ElideRight)
    t.setMinimumHeight(108)
    t._num, t._mono = set(num_cols), set(mono_cols) | set(num_cols)
    for c in pill_cols:
        t.setItemDelegateForColumn(c, StatusDelegate(t))
    for c in bar_cols:
        t.setItemDelegateForColumn(c, BarDelegate(t))
    for c in num_cols:
        t.horizontalHeaderItem(c).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return t


def fill(t, rows, widths=None, icons=None):
    """Komórka: tekst, krotka (tekst, klucz statusu) albo ('', None, ułamek) dla paska. icons: {wiersz: QIcon} dla kolumny 0."""
    t.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            if isinstance(v, tuple):
                it = QTableWidgetItem(v[0]); it.setData(ROLE_KEY, v[1])
                if len(v) > 2:
                    it.setData(ROLE_BAR, v[2])
            else:
                it = QTableWidgetItem(str(v))
            if c in t._mono:
                it.setFont(mono(12))
            if c in t._num:
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if c == 0 and icons and icons.get(r):
                it.setIcon(icons[r])
            it.setToolTip(it.text())
            t.setItem(r, c, it)
    if widths:
        for c, w in enumerate(widths):
            if w:
                t.setColumnWidth(c, w)


def fit_height(t, max_rows=None):
    """Dopasowuje wysokość tabeli do liczby wierszy, żeby pod nią nie zostawała pusta przestrzeń."""
    n = t.rowCount() if max_rows is None else min(t.rowCount(), max_rows)
    t.setMinimumHeight(0); t.setFixedHeight(36 + 36 * n + 4)


class MetricCard(QFrame):
    """Etykieta, liczba, opis i opcjonalny cienki pasek. Wszystkie karty mają tę samą budowę i wysokość."""

    def __init__(self, label, bar=True):
        super().__init__(); self.setObjectName("card"); self.setFixedHeight(112)
        lay = QVBoxLayout(self); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(0)
        self.label = QLabel(label); self.label.setObjectName("cap")
        self.value = QLabel("—"); self.value.setObjectName("metric")
        self.note = QLabel(""); self.note.setObjectName("muted")
        self.bar = QProgressBar(); self.bar.setRange(0, 100); self.bar.setTextVisible(False)
        sp = self.bar.sizePolicy(); sp.setRetainSizeWhenHidden(True); self.bar.setSizePolicy(sp)
        self.bar.setVisible(bar)
        for w in (self.label, self.value, self.note):
            lay.addWidget(w)
        lay.addStretch(1); lay.addWidget(self.bar)

    def set(self, value, note="", pct=None):
        self.value.setText(value); self.note.setText(note)
        if pct is not None:
            self.bar.setValue(int(pct))
            col = "#d97706" if pct >= 85 else "#52525b"
            self.bar.setStyleSheet(f"QProgressBar::chunk {{ background: {col}; border-radius: 2px; }}")


class SegBar(QWidget):
    """Pasek zajętości dysku podzielony na foldery i wolne miejsce. Jedyny mocno kolorowy element ekranu."""
    COLORS = [ACCENT, "#52525b", "#71717a", "#a1a1aa"]

    def __init__(self):
        super().__init__(); self.segs = []; self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(64)

    def set(self, segs):
        """segs: lista (etykieta, bajty, kolor lub None), kolejność od lewej."""
        self.segs = [s for s in segs if s[1] > 0]; self.update()

    def paintEvent(self, _):
        if not self.segs:
            return
        total = sum(s[1] for s in self.segs); w = self.width()
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
        x, gap = 0.0, 2.0
        for i, (label, size, color) in enumerate(self.segs):
            sw = max(3.0, (w - gap * (len(self.segs) - 1)) * size / total)
            p.setBrush(QColor(color)); r = QRectF(x, 0, sw, 28)
            p.drawRoundedRect(r, 6, 6)
            x += sw + gap
        f = QFont("Segoe UI"); f.setPixelSize(12); p.setFont(f)
        lx, ly = 0, 52
        for label, size, color in self.segs:
            txt, val = label, _gb(size)
            tw = QFontMetrics(f).horizontalAdvance(txt) + QFontMetrics(mono(12)).horizontalAdvance(val) + 40
            if lx + tw > w and lx > 0:
                lx, ly = 0, ly + 20
            p.setPen(Qt.NoPen); p.setBrush(QColor(color)); p.drawRoundedRect(QRectF(lx, ly - 8, 8, 8), 2, 2)
            p.setPen(QColor(INK2)); p.setFont(f); p.drawText(lx + 14, ly, txt)
            ax = lx + 14 + QFontMetrics(f).horizontalAdvance(txt) + 8
            p.setPen(QColor(INK3)); p.setFont(mono(12)); p.drawText(ax, ly, val)
            lx += tw
        p.end()


def _gb(n):
    return f"{n / 1024 ** 3:.1f}".replace(".", ",") + " GB"


def tool_button(text, changes=False, tip=""):
    """Cichy przycisk narzędzia. Pusta kropka: tylko otwiera narzędzie. Pełna: zmienia system po potwierdzeniu."""
    b = QPushButton(("●  " if changes else "○  ") + text); b.setObjectName("tool"); b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor); return b


def marker_legend():
    l = QLabel("○ otwiera narzędzie lub ustawienia      ● zmienia system, po Twoim potwierdzeniu"); l.setObjectName("muted"); return l


class Worker(QThread):
    done = Signal(object)
    msg = Signal(str)

    def __init__(self, fn, pass_progress=False):
        super().__init__(); self.fn, self.pp = fn, pass_progress

    def run(self):
        try:
            self.done.emit(self.fn(self.msg.emit) if self.pp else self.fn())
        except Exception as e:
            self.done.emit({"__error__": str(e)})


class Page(QWidget):
    """Strona: nagłówek i akcje, cienki pasek zajętości, treść, status."""
    scanned = Signal()

    def __init__(self, title, subtitle, scan_fn, pass_progress=False, button="Skanuj"):
        super().__init__()
        self.scan_fn, self.pp, self.data, self.worker, self.built = scan_fn, pass_progress, None, None, False
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 20, 24, 12); lay.setSpacing(12)
        top = QHBoxLayout(); box = QVBoxLayout(); box.setSpacing(0)
        h = QLabel(title); h.setObjectName("h"); s = QLabel(subtitle); s.setObjectName("sub")
        box.addWidget(h); box.addWidget(s); top.addLayout(box, 1)
        self.actions = QHBoxLayout(); self.actions.setSpacing(8); top.addLayout(self.actions)
        self.btn = QPushButton(button); self.btn.setObjectName("primary"); self.btn.clicked.connect(self.run)
        self.actions.addWidget(self.btn)
        lay.addLayout(top)
        self.busy = QProgressBar(); self.busy.setObjectName("busy"); self.busy.setRange(0, 0); self.busy.setTextVisible(False); self.busy.hide()
        lay.addWidget(self.busy)
        self.body = QVBoxLayout(); self.body.setSpacing(12); lay.addLayout(self.body, 1)
        self.status = QLabel("Skan tylko odczytuje dane"); self.status.setObjectName("status")
        lay.addWidget(self.status)

    def build(self): ...
    def render(self, data): return ""

    def run(self):
        if self.worker and self.worker.isRunning():
            return
        self.btn.setEnabled(False); self.busy.show(); self.status.setText("Skanowanie…")
        self.worker = Worker(self.scan_fn, self.pp)
        self.worker.msg.connect(self.status.setText)
        self.worker.done.connect(self._finish)
        self.worker.start()

    def _finish(self, data):
        self.btn.setEnabled(True); self.busy.hide()
        if isinstance(data, dict) and "__error__" in data:
            self.status.setText("Błąd skanu: " + data["__error__"]); return
        self.data = data
        if not self.built:
            self.build(); self.built = True
        self.status.setText(f"{self.render(data)}  ·  {datetime.now():%H:%M:%S}")
        self.scanned.emit()
