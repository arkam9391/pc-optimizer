"""Elementy interfejsu. Kierunek: grafit, jeden akcent (kobalt), liczby w mono, statusy jako kropki."""
from datetime import datetime

from PySide6.QtCore import QRectF, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QSizePolicy, QStyle, QStyledItemDelegate, QStyleOptionViewItem,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

# --- tokeny: wartości pochodzą z aktywnego motywu (theme.py) ---------------
from theme import (ACCENT, CARD, DOT, ICON, ICON_DIM, INK, INK2, INK3, LINE, MONO, PAGE, RAISED, SEG_COLORS, SEG_FREE,  # noqa: E402
                   SEG_REST, SEG_USED, SIDE, STYLE, T, THEME, THEMES, make_palette, save_theme)

ROLE_KEY, ROLE_BAR = Qt.UserRole + 1, Qt.UserRole + 2


def glyph_icon(ch, color=INK3, px=30):
    pm = QPixmap(40, 40); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.TextAntialiasing)
    f = QFont("Segoe MDL2 Assets"); f.setPixelSize(px); p.setFont(f); p.setPen(QColor(color))
    p.drawText(pm.rect(), Qt.AlignCenter, ch); p.end()
    return QIcon(pm)


def logo_pixmap(px):
    """Znak aplikacji: grafitowy kwadrat z paskiem zajętości dysku (kobalt = największy folder, szary = reszta, jasny = wolne)."""
    pm = QPixmap(px, px); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
    p.setBrush(QColor("#171717")); p.drawRoundedRect(QRectF(0, 0, px, px), px * 0.22, px * 0.22)
    pad, gap = px * 0.16, px * 0.045
    bar_h = px * 0.34; y = (px - bar_h) / 2; w = px - 2 * pad - 2 * gap
    x = pad
    for frac, color in ((0.50, "#2b59c3"), (0.22, "#8a8a93"), (0.28, "#ececee")):
        sw = w * frac
        p.setBrush(QColor(color)); p.drawRoundedRect(QRectF(x, y, sw, bar_h), px * 0.07, px * 0.07)
        x += sw + gap
    p.end()
    return pm


def app_icon():
    ic = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        ic.addPixmap(logo_pixmap(s))
    return ic


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
        p.setBrush(QColor(ACCENT if frac >= 0.999 else T["BAR_LOW"]))
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
            col = T["WARN"] if pct >= 85 else T["BAR"]
            self.bar.setStyleSheet(f"QProgressBar::chunk {{ background: {col}; border-radius: 2px; }}")


class SegBar(QWidget):
    """Pasek zajętości dysku podzielony na foldery i wolne miejsce. Jedyny mocno kolorowy element ekranu."""
    COLORS = SEG_COLORS

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
