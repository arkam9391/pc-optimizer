"""Motywy kolorów. Jasny to motyw bazowy, trzy ciemne dzielą ten sam układ i inaczej dobierają neutralne kolory oraz akcent.
Motyw wybiera się przy starcie (zmienna PCOPT_THEME, argument --theme albo zapis w ustawieniach), bo tokeny trafiają do arkusza stylów."""
import json
import os
import sys
from pathlib import Path

from PySide6.QtGui import QColor, QPalette

THEMES = {
    "jasny": dict(
        label="Jasny", INK="#171717", INK2="#525252", INK3="#737373", LINE="#e6e6e8", PAGE="#fafafa", CARD="#ffffff",
        SIDE="#f4f4f5", RAISED="#ececee", ACCENT="#2b59c3", SELECT="#e4e4e7", SELECT_LINE="#c9c9ce", BTN_LINE="#d9d9dc",
        ROW_LINE="#f0f0f1", HANDLE="#d4d4d8", HOVER="#f4f4f5", PRESSED="#ececee", PRI_BG="#171717", PRI_FG="#ffffff",
        PRI_HOVER="#333333", OFF_BG="#a1a1aa", OFF_FG="#ffffff", DISABLED="#a1a1aa", BAR="#52525b", BAR_LOW="#a1a1aa",
        WARN="#d97706", SEG=("#52525b", "#71717a", "#a1a1aa"), SEG_REST="#d4d4d8", SEG_FREE="#ececee",
        DOT_WARN="#d97706", DOT_BAD="#dc2626", DOT_OK="#16a34a", DOT_NEUTRAL="#a1a1aa", ICON="#737373", ICON_DIM="#a1a1aa"),
    # neutralny grafit, kobalt rozjaśniony do ciemnego tła
    "grafit": dict(
        label="Grafit", INK="#ececee", INK2="#b4b4bb", INK3="#8b8b94", LINE="#2a2a2f", PAGE="#121214", CARD="#1b1b1f",
        SIDE="#18181b", RAISED="#27272a", ACCENT="#6b8eea", SELECT="#2a2a2f", SELECT_LINE="#3a3a41", BTN_LINE="#34343a",
        ROW_LINE="#232328", HANDLE="#3a3a41", HOVER="#232328", PRESSED="#2a2a30", PRI_BG="#ececee", PRI_FG="#121214",
        PRI_HOVER="#ffffff", OFF_BG="#3a3a41", OFF_FG="#8b8b94", DISABLED="#5c5c64", BAR="#71717a", BAR_LOW="#6b6b75",
        WARN="#f59e0b", SEG=("#8b8b95", "#62626c", "#484850"), SEG_REST="#3c3c44", SEG_FREE="#2e2e34",
        DOT_WARN="#f59e0b", DOT_BAD="#f87171", DOT_OK="#4ade80", DOT_NEUTRAL="#6b6b75", ICON="#8b8b94", ICON_DIM="#5c5c64"),
    # chłodna czerń przyrządów nocą, akcent morski
    "polnoc": dict(
        label="Północ", INK="#e6edf3", INK2="#aab4c2", INK3="#808c9b", LINE="#232b36", PAGE="#0d1117", CARD="#151b23",
        SIDE="#10151c", RAISED="#1f2731", ACCENT="#2dd4bf", SELECT="#1f2731", SELECT_LINE="#2f3a48", BTN_LINE="#2b3441",
        ROW_LINE="#1b222c", HANDLE="#2f3a48", HOVER="#1b222c", PRESSED="#232b36", PRI_BG="#e6edf3", PRI_FG="#0d1117",
        PRI_HOVER="#ffffff", OFF_BG="#2f3a48", OFF_FG="#808c9b", DISABLED="#566170", BAR="#6b7889", BAR_LOW="#5f6b7a",
        WARN="#f59e0b", SEG=("#8794a6", "#5f6b7a", "#434d5a"), SEG_REST="#364352", SEG_FREE="#25303c",
        DOT_WARN="#f59e0b", DOT_BAD="#f87171", DOT_OK="#4ade80", DOT_NEUTRAL="#5f6b7a", ICON="#808c9b", ICON_DIM="#566170"),
    # prawie czarny, ciepła biel zamiast koloru: akcentem jest jasność
    "wegiel": dict(
        label="Węgiel", INK="#f2efe9", INK2="#b5b0a7", INK3="#8c877e", LINE="#262626", PAGE="#0a0a0a", CARD="#141414",
        SIDE="#0f0f0f", RAISED="#1f1f1f", ACCENT="#f2efe9", SELECT="#232323", SELECT_LINE="#333333", BTN_LINE="#2e2e2e",
        ROW_LINE="#1c1c1c", HANDLE="#333333", HOVER="#1c1c1c", PRESSED="#262626", PRI_BG="#f2efe9", PRI_FG="#0a0a0a",
        PRI_HOVER="#ffffff", OFF_BG="#333333", OFF_FG="#8c877e", DISABLED="#5a5750", BAR="#8c877e", BAR_LOW="#5f5b54",
        WARN="#f59e0b", SEG=("#8c877e", "#625e57", "#45423d"), SEG_REST="#363430", SEG_FREE="#2a2a2a",
        DOT_WARN="#f59e0b", DOT_BAD="#f87171", DOT_OK="#4ade80", DOT_NEUTRAL="#625e57", ICON="#8c877e", ICON_DIM="#5a5750"),
}
SETTINGS = Path(os.environ.get("APPDATA", ".")) / "PCOptimizer" / "settings.json"


def _pick_theme():
    """Kolejność: zmienna PCOPT_THEME, argument --theme <nazwa>, zapis z ustawień, jasny."""
    name = os.environ.get("PCOPT_THEME")
    if not name and "--theme" in sys.argv[:-1]:
        name = sys.argv[sys.argv.index("--theme") + 1]
    if not name:
        try:
            name = json.loads(SETTINGS.read_text("utf-8")).get("theme")
        except (OSError, ValueError, AttributeError):
            name = None
    return name if name in THEMES else "jasny"


def save_theme(name):
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps({"theme": name}), "utf-8")


THEME = _pick_theme(); T = THEMES[THEME]
INK, INK2, INK3 = T["INK"], T["INK2"], T["INK3"]
LINE, PAGE, CARD, SIDE, RAISED = T["LINE"], T["PAGE"], T["CARD"], T["SIDE"], T["RAISED"]
ACCENT = T["ACCENT"]
SEG_COLORS = [ACCENT, *T["SEG"]]
SEG_USED, SEG_REST, SEG_FREE = T["SEG"][0], T["SEG_REST"], T["SEG_FREE"]
ICON, ICON_DIM = T["ICON"], T["ICON_DIM"]
MONO = "Consolas"
DOT = {  # klucz: (kolor kropki, wypełniona?, kolor tekstu)
    "warn": (T["DOT_WARN"], True, INK), "bad": (T["DOT_BAD"], True, INK), "ok": (T["DOT_OK"], True, INK2),
    "info": (T["DOT_NEUTRAL"], False, INK2), "gray": (T["DOT_NEUTRAL"], False, INK3),
}

STYLE = f"""
* {{ font-family: "Segoe UI"; font-size: 13px; color: {INK}; }}
QMainWindow, #root, #content {{ background: {PAGE}; }}
QMessageBox, QDialog {{ background: {PAGE}; }}
QToolTip {{ background: {CARD}; color: {INK}; border: 1px solid {LINE}; padding: 4px 8px; }}
#side {{ background: {SIDE}; border-right: 1px solid {LINE}; }}
#brand {{ font-size: 16px; font-weight: 500; padding: 4px 12px 16px 12px; }}
QPushButton#nav {{ text-align: left; padding: 8px 12px; border: none; border-radius: 8px; background: transparent; color: {INK2}; }}
QPushButton#nav:hover {{ background: {RAISED}; }}
QPushButton#nav:checked {{ background: {T["SELECT"]}; color: {INK}; font-weight: 500; }}
QPushButton {{ padding: 8px 16px; border: 1px solid {T["BTN_LINE"]}; border-radius: 8px; background: {CARD}; }}
QPushButton:hover {{ background: {T["HOVER"]}; }}
QPushButton:pressed {{ background: {T["PRESSED"]}; }}
QPushButton:disabled {{ color: {T["DISABLED"]}; background: {PAGE}; }}
QPushButton#primary {{ background: {T["PRI_BG"]}; color: {T["PRI_FG"]}; border: none; }}
QPushButton#primary:hover {{ background: {T["PRI_HOVER"]}; }}
QPushButton#primary:disabled {{ background: {T["OFF_BG"]}; color: {T["OFF_FG"]}; }}
QPushButton#chip {{ padding: 4px 12px; color: {INK2}; }}
QPushButton#chip:checked {{ background: {T["SELECT"]}; color: {INK}; border-color: {T["SELECT_LINE"]}; }}
QPushButton#tool {{ text-align: left; padding: 8px 12px; border: none; background: transparent; }}
QPushButton#tool:hover {{ background: {RAISED}; }}
QComboBox {{ padding: 6px 10px; border: 1px solid {T["BTN_LINE"]}; border-radius: 8px; background: {CARD}; }}
QComboBox:hover {{ background: {T["HOVER"]}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {CARD}; border: 1px solid {LINE}; selection-background-color: {T["SELECT"]};
  selection-color: {INK}; outline: 0; }}
QLabel#h {{ font-size: 24px; font-weight: 500; }}
QLabel#sub {{ color: {INK2}; }}
QLabel#muted {{ color: {INK3}; font-size: 12px; }}
QLabel#status {{ color: {INK3}; font-size: 12px; }}
QLabel#cap {{ color: {INK2}; font-size: 12px; }}
#card, #box {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 12px; }}
QLabel#metric {{ font-family: {MONO}; font-size: 26px; }}
QProgressBar {{ background: {LINE}; border: none; border-radius: 2px; max-height: 4px; min-height: 4px; }}
QProgressBar::chunk {{ background: {T["BAR"]}; border-radius: 2px; }}
QProgressBar#busy {{ max-height: 2px; min-height: 2px; }}
QProgressBar#busy::chunk {{ background: {ACCENT}; }}
QTableWidget {{ border: 1px solid {LINE}; border-radius: 12px; gridline-color: transparent; background: {CARD};
  selection-background-color: {T["HOVER"]}; selection-color: {INK}; outline: 0; }}
QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid {T["ROW_LINE"]}; }}
QHeaderView::section {{ background: {CARD}; border: none; border-bottom: 1px solid {LINE}; padding: 8px; color: {INK3}; font-size: 12px; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ padding: 8px 12px; margin-right: 4px; border-radius: 8px; background: transparent; color: {INK2}; }}
QTabBar::tab:selected {{ background: {T["SELECT"]}; color: {INK}; }}
QPlainTextEdit {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 12px; padding: 8px; }}
QScrollBar:vertical {{ width: 8px; background: transparent; margin: 4px 0; }}
QScrollBar::handle:vertical {{ background: {T["HANDLE"]}; border-radius: 4px; min-height: 32px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: {T["HANDLE"]}; border-radius: 4px; min-width: 32px; }}
"""


def make_palette():
    """Paleta Qt z tokenów motywu: obejmuje okna dialogowe i elementy, których nie dotyka arkusz stylów."""
    p = QPalette()
    for role, col in ((QPalette.Window, PAGE), (QPalette.WindowText, INK), (QPalette.Base, CARD), (QPalette.AlternateBase, SIDE),
                      (QPalette.Text, INK), (QPalette.Button, CARD), (QPalette.ButtonText, INK), (QPalette.ToolTipBase, CARD),
                      (QPalette.ToolTipText, INK), (QPalette.PlaceholderText, INK3), (QPalette.Highlight, T["SELECT"]),
                      (QPalette.HighlightedText, INK), (QPalette.Link, ACCENT)):
        p.setColor(role, QColor(col))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, QColor(T["DISABLED"]))
    return p
