"""
theme.py
========
Design tokens for the app. Centralized so every widget pulls from the same
small palette instead of scattering hex literals through widget code.

Design direction: this app's entire subject is a keyboard that emits light
in a dark room — that's the actual product experience, not an abstraction.
So the UI itself is dark-and-quiet by default (near-black, restrained
grays), with the ONE accent color reserved for the thing the keyboard
itself does: the live effect swatches render their real colors against
this dark field, the same way the keys would against a dark desk. That's
the one place full saturation appears. Everything else — chrome, controls,
status text — stays deliberately muted so the swatches read as the
brightest, most alive thing on screen, the way LEDs read in a dim room.

Palette (named, not just hex):
  - void       #15171C   base background, the "off keyboard" black
  - panel      #1C1F26   raised surface (effect cards, sleep panel)
  - panel_hi   #242832   hover/active surface
  - hairline   #2D3038   borders, dividers — barely-there
  - ink        #E8E9ED   primary text
  - ink_dim    #8B8F9C   secondary text, captions
  - ink_faint  #565A66   disabled / tertiary
  - signal     #5EE6A8   single accent — connection-good, primary actions
                          (a cool mint, distinct from any RGB effect hue,
                          so it never gets lost among the swatches)
  - warn       #E6A85E   degraded state (no permission, needs setup)
  - danger     #E65E6E   disconnected / error state
"""
from __future__ import annotations

VOID = "#15171C"
PANEL = "#1C1F26"
PANEL_HI = "#242832"
HAIRLINE = "#2D3038"

INK = "#E8E9ED"
INK_DIM = "#8B8F9C"
INK_FAINT = "#565A66"

SIGNAL = "#5EE6A8"
SIGNAL_DIM = "#3D9C72"
WARN = "#E6A85E"
DANGER = "#E65E6E"

# Type: a slightly condensed, technical display face for the title/header
# (mono-leaning, since this whole app is "talking to" a CLI underneath),
# and a clean, neutral UI face for everything readable in volume. Falls
# back gracefully if these aren't installed — Qt will substitute silently.
FONT_DISPLAY = "JetBrains Mono"
FONT_UI = "Inter"
FONT_FALLBACK = "Noto Sans, DejaVu Sans, sans-serif"

RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32


def state_color(state_name: str) -> str:
    """Maps a ConnectionState.value string to its status color."""
    return {
        "wired": SIGNAL,
        "wireless": SIGNAL,
        "disconnected": DANGER,
        "no_permission": WARN,
    }.get(state_name, INK_DIM)


STYLESHEET = f"""
QWidget {{
    background-color: {VOID};
    color: {INK};
    font-family: "{FONT_UI}", {FONT_FALLBACK};
    font-size: 13px;
}}

QMainWindow {{
    background-color: {VOID};
}}

#TitleBar {{
    background-color: {VOID};
    border-bottom: 1px solid {HAIRLINE};
}}

#AppTitle {{
    font-family: "{FONT_DISPLAY}", monospace;
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: {INK};
}}

#StatusPill {{
    border-radius: {RADIUS_LG}px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}

#SectionLabel {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: {INK_FAINT};
    text-transform: uppercase;
}}

#EffectCard {{
    background-color: {PANEL};
    border: 1px solid {HAIRLINE};
    border-radius: {RADIUS_MD}px;
}}

#EffectCard[active="true"] {{
    border: 1px solid {SIGNAL_DIM};
    background-color: {PANEL_HI};
}}

#EffectCard:hover {{
    background-color: {PANEL_HI};
}}

#EffectName {{
    font-size: 13px;
    font-weight: 500;
    color: {INK};
}}

#EffectCode {{
    font-family: "{FONT_DISPLAY}", monospace;
    font-size: 10px;
    color: {INK_FAINT};
}}

QPushButton {{
    background-color: {PANEL};
    border: 1px solid {HAIRLINE};
    border-radius: {RADIUS_SM}px;
    padding: 8px 16px;
    color: {INK};
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {PANEL_HI};
    border: 1px solid {SIGNAL_DIM};
}}

QPushButton:pressed {{
    background-color: {VOID};
}}

QPushButton:disabled {{
    color: {INK_FAINT};
    border: 1px solid {HAIRLINE};
}}

QPushButton#PrimaryButton {{
    background-color: {SIGNAL};
    color: {VOID};
    border: none;
    font-weight: 700;
}}

QPushButton#PrimaryButton:hover {{
    background-color: #74EFB6;
}}

QPushButton#PrimaryButton:disabled {{
    background-color: {HAIRLINE};
    color: {INK_FAINT};
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {HAIRLINE};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {SIGNAL};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::sub-page:horizontal {{
    background: {SIGNAL_DIM};
    border-radius: 2px;
}}

QSpinBox {{
    background-color: {PANEL};
    border: 1px solid {HAIRLINE};
    border-radius: {RADIUS_SM}px;
    padding: 4px 8px;
}}

#ToggleSwitch[checked="true"] {{
    background-color: {SIGNAL};
}}

#ToggleSwitch[checked="false"] {{
    background-color: {HAIRLINE};
}}

#ErrorBanner {{
    background-color: rgba(230, 94, 110, 0.12);
    border: 1px solid {DANGER};
    border-radius: {RADIUS_SM}px;
    color: {INK};
    padding: 12px;
}}

#WarnBanner {{
    background-color: rgba(230, 168, 94, 0.12);
    border: 1px solid {WARN};
    border-radius: {RADIUS_SM}px;
    color: {INK};
    padding: 12px;
}}

QScrollArea {{
    border: none;
}}

QScrollBar:vertical {{
    background: {VOID};
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: {HAIRLINE};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {INK_FAINT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
