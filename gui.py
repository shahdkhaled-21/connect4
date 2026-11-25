"""
gui.py - Pygame GUI: human vs. minimax AI, with live AI stats, unified top header,
tactile action buttons with native vector icons, and an interactive tree panel
with an integrated Node Inspector.

Controls:
    - Click column / [1-7]: Drop a disc
    - [T] / Click 'TREE [T]': Toggle minimax decision tree & inspector panel
    - [R] / Click 'RESET [R]': Restart game
    - [Esc]: Quit
"""

import ctypes
import math
import os
import threading
import pygame

# Enable Windows Per-Monitor High-DPI awareness before Pygame initializes.
# This prevents Windows DWM from bitmap-stretching the window, eliminating blurriness & pixelation.
if os.name == "nt":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from ai import choose_move
from engine import (ROWS, COLS, EMPTY, HUMAN, COMPUTER, new_board, four_cells,
                    get_valid_moves, drop_piece, get_scores, is_full, winner)
from tree import fmt_bound, node_label, node_tail
from tree_view import default_expanded, expand_all, principal_path, visible_rows

# ---------- Layout & Geometry (Comfortable Large Scale) ----------
SQUARE = 94                           # pixel size of one cell (crisp large board)
PAD_X = 26                            # horizontal margin around the board
SCORE_H = 96                          # height of the top scoreboard bar
HOVER_H = 86                          # height of hover guide zone
TOP = SCORE_H + HOVER_H               # top coordinate of the board (182)
HOVER_Y = SCORE_H + HOVER_H // 2      # resting vertical center for hover disc
RADIUS = SQUARE // 2 - 10             # radius of a hole / disc (37px)
WIDTH = COLS * SQUARE + 2 * PAD_X     # 710px base board width
BOARD_RECT = pygame.Rect(PAD_X, TOP, COLS * SQUARE, ROWS * SQUARE)
STATS_H = 92                          # height of the AI-stats strip under the board
STATS_RECT = pygame.Rect(PAD_X, BOARD_RECT.bottom + 12, WIDTH - 2 * PAD_X, STATS_H)
HEIGHT = STATS_RECT.bottom + 14       # total window height (864px)
PANEL_W = 620                         # width of the tree panel (added to the right)
PANEL_RECT = pygame.Rect(WIDTH, SCORE_H, PANEL_W, HEIGHT - SCORE_H)

# ---------- Palette: Sleek Midnight Glass ----------
BG_TOP = (16, 20, 42)                 # midnight indigo
BG_BOTTOM = (8, 10, 20)               # deep abyss
BOARD_BASE = (22, 30, 62)             # sleek chassis color
BOARD_BORDER = (46, 62, 118)          # chassis rim highlight
BOARD_LIP = (70, 92, 170)             # top edge highlight
HOLE_BACK = (11, 14, 28)              # deep socket interior
HOLE_SHADOW = (5, 7, 16)              # countersunk top inner shadow
HOLE_RIM = (44, 58, 108)              # bottom rim bevel

# Discs (3D Polished Ceramic / Gem tones)
RUBY_RED = (235, 52, 82)              # Human disc primary
AMBER_GOLD = (250, 188, 38)           # Computer disc primary
TEXT_WHITE = (244, 247, 255)          # primary text
TEXT_MUTED = (145, 155, 190)          # secondary text
PRUNED_GREY = (88, 98, 128)           # greyed-out (pruned) tree rows
LEAF_GREEN = (120, 215, 150)          # heuristic leaves
FINAL_BLUE = (140, 195, 255)          # exact (full-board) leaves

DISC_COLORS = {HUMAN: RUBY_RED, COMPUTER: AMBER_GOLD}
SS = 4                                # supersampling factor for antialiasing


# ==============================================================================
# Supersampled Anti-Aliased Vector Graphics (Ultra-Smooth Quality)
# ==============================================================================

_smooth_icon_cache = {}


def get_smooth_icon(name, size, color):
    """
    Render a vector icon at 4x supersampling and smoothscale down for
    subpixel anti-aliasing without any pixelated or jagged edges.
    """
    key = (name, size, tuple(color) if isinstance(color, (list, tuple)) else color)
    if key in _smooth_icon_cache:
        return _smooth_icon_cache[key]

    factor = 4
    dim = size * factor
    surf = pygame.Surface((dim, dim), pygame.SRCALPHA)
    c = dim / 2.0
    r = (dim - 4) / 2.0

    if name == "star":
        pts = []
        for i in range(10):
            angle = i * math.pi / 5 - math.pi / 2
            rad = r if (i % 2 == 0) else (r * 0.44)
            pts.append((c + rad * math.cos(angle), c + rad * math.sin(angle)))
        pygame.draw.polygon(surf, color, pts)

    elif name == "search":
        cr = r * 0.52
        offset = r * 0.22
        pygame.draw.circle(surf, color, (int(c - offset), int(c - offset)), int(cr), int(2.4 * factor))
        pygame.draw.line(surf, color,
                         (int(c + offset * 0.5), int(c + offset * 0.5)),
                         (int(c + r * 0.85), int(c + r * 0.85)),
                         int(2.6 * factor))

    elif name == "reset":
        arc_r = r * 0.72
        arc_rect = pygame.Rect(c - arc_r, c - arc_r, arc_r * 2, arc_r * 2)
        pygame.draw.arc(surf, color, arc_rect, math.pi * 0.22, math.pi * 1.82, int(2.4 * factor))
        tip_x = c + arc_r * math.cos(math.pi * 0.22)
        tip_y = c - arc_r * math.sin(math.pi * 0.22)
        pts = [(tip_x, tip_y - 4.5 * factor), (tip_x + 5.0 * factor, tip_y + 1.5 * factor), (tip_x - 3.5 * factor, tip_y + 2.5 * factor)]
        pygame.draw.polygon(surf, color, pts)

    elif name == "cut":
        s = r * 0.65
        pygame.draw.line(surf, color, (c - s, c - s), (c + s, c + s), int(2.2 * factor))
        pygame.draw.line(surf, color, (c - s, c + s), (c + s, c - s), int(2.2 * factor))

    elif name == "cross":
        s = r * 0.62
        pygame.draw.line(surf, color, (c - s, c - s), (c + s, c + s), int(2.2 * factor))
        pygame.draw.line(surf, color, (c - s, c + s), (c + s, c - s), int(2.2 * factor))

    elif name.startswith("triangle_"):
        direction = name.split("_")[1]
        s = r * 0.75
        if direction == "down":
            pts = [(c - s, c - s * 0.6), (c + s, c - s * 0.6), (c, c + s * 0.7)]
        elif direction == "up":
            pts = [(c, c - s * 0.7), (c - s, c + s * 0.6), (c + s, c + s * 0.6)]
        elif direction == "right":
            pts = [(c - s * 0.6, c - s), (c + s * 0.7, c), (c - s * 0.6, c + s)]
        else:
            pts = [(c + s * 0.6, c - s), (c - s * 0.7, c), (c + s * 0.6, c + s)]
        pygame.draw.polygon(surf, color, pts)

    elif name == "gem":
        pygame.draw.circle(surf, color, (int(c), int(c)), int(r))
        pygame.draw.circle(surf, (255, 255, 255, 220), (int(c - r * 0.32), int(c - r * 0.32)), int(r * 0.35))

    elif name == "ring":
        pygame.draw.circle(surf, color, (int(c), int(c)), int(r), int(2.6 * factor))

    elif name == "hover_arrow":
        pts = [(c, c + r), (c - r * 0.8, c - r * 0.5), (c + r * 0.8, c - r * 0.5)]
        pygame.draw.polygon(surf, color, pts)

    elif name == "home":
        # Roof triangle
        roof = [(c, c - r * 0.72), (c - r * 0.85, c + r * 0.05), (c + r * 0.85, c + r * 0.05)]
        pygame.draw.polygon(surf, color, roof)
        # Body
        body = pygame.Rect(c - r * 0.60, c, r * 1.20, r * 0.72)
        pygame.draw.rect(surf, color, body)
        # Door cutout
        door = pygame.Rect(c - r * 0.20, c + r * 0.26, r * 0.40, r * 0.48)
        pygame.draw.rect(surf, (0, 0, 0, 0), door)

    elif name in ("fullscreen", "windowed"):
        d = r * 0.72
        t = int(2.4 * factor)
        leg = r * 0.38
        if name == "fullscreen":
            # 4 corner brackets expanding outwards
            pygame.draw.line(surf, color, (c - d, c - d), (c - d + leg, c - d), t)
            pygame.draw.line(surf, color, (c - d, c - d), (c - d, c - d + leg), t)
            pygame.draw.line(surf, color, (c + d, c - d), (c + d - leg, c - d), t)
            pygame.draw.line(surf, color, (c + d, c - d), (c + d, c - d + leg), t)
            pygame.draw.line(surf, color, (c - d, c + d), (c - d + leg, c + d), t)
            pygame.draw.line(surf, color, (c - d, c + d), (c - d, c + d - leg), t)
            pygame.draw.line(surf, color, (c + d, c + d), (c + d - leg, c + d), t)
            pygame.draw.line(surf, color, (c + d, c + d), (c + d, c + d - leg), t)
        else:
            # 4 corner brackets collapsing inwards (windowed)
            pygame.draw.line(surf, color, (c - d + leg, c - d + leg), (c - d, c - d + leg), t)
            pygame.draw.line(surf, color, (c - d + leg, c - d + leg), (c - d + leg, c - d), t)
            pygame.draw.line(surf, color, (c + d - leg, c - d + leg), (c + d, c - d + leg), t)
            pygame.draw.line(surf, color, (c + d - leg, c - d + leg), (c + d - leg, c - d), t)
            pygame.draw.line(surf, color, (c - d + leg, c + d - leg), (c - d, c + d - leg), t)
            pygame.draw.line(surf, color, (c - d + leg, c + d - leg), (c - d + leg, c + d), t)
            pygame.draw.line(surf, color, (c + d - leg, c + d - leg), (c + d, c + d - leg), t)
            pygame.draw.line(surf, color, (c + d - leg, c + d - leg), (c + d - leg, c + d), t)

    res = pygame.transform.smoothscale(surf, (size, size))
    _smooth_icon_cache[key] = res
    return res


def draw_icon_reset(surf, cx, cy, radius=6, color=TEXT_WHITE):
    """Draw a smooth antialiased circular arrow icon."""
    size = radius * 2 + 6
    ico = get_smooth_icon("reset", size, color)
    surf.blit(ico, (cx - size // 2, cy - size // 2))


def draw_icon_star(surf, cx, cy, r=7, color=AMBER_GOLD):
    """Draw a smooth antialiased 5-pointed star icon."""
    size = r * 2 + 4
    ico = get_smooth_icon("star", size, color)
    surf.blit(ico, (cx - size // 2, cy - size // 2))


def draw_icon_search(surf, cx, cy, r=6, color=AMBER_GOLD):
    """Draw a smooth antialiased magnifying glass icon."""
    size = r * 2 + 8
    ico = get_smooth_icon("search", size, color)
    surf.blit(ico, (cx - size // 2, cy - size // 2))


def draw_icon_cut(surf, cx, cy, size=5, color=(255, 140, 160)):
    """Draw a smooth antialiased cut cross icon."""
    dim = size * 2 + 4
    ico = get_smooth_icon("cut", dim, color)
    surf.blit(ico, (cx - dim // 2, cy - dim // 2))


def draw_icon_triangle(surf, cx, cy, size=5, direction="down", color=TEXT_WHITE):
    """Draw a smooth antialiased directional triangle icon."""
    dim = size * 2 + 4
    ico = get_smooth_icon(f"triangle_{direction}", dim, color)
    surf.blit(ico, (cx - dim // 2, cy - dim // 2))


def draw_icon_cross(surf, cx, cy, size=5, color=TEXT_WHITE):
    """Draw a smooth antialiased X close icon."""
    dim = size * 2 + 4
    ico = get_smooth_icon("cross", dim, color)
    surf.blit(ico, (cx - dim // 2, cy - dim // 2))


def draw_icon_fullscreen(surf, cx, cy, size=6, is_fs=False, color=TEXT_WHITE):
    """Draw a smooth antialiased fullscreen or windowed toggle icon."""
    dim = size * 2 + 6
    ico = get_smooth_icon("windowed" if is_fs else "fullscreen", dim, color)
    surf.blit(ico, (cx - dim // 2, cy - dim // 2))


def draw_icon_home(surf, cx, cy, size=6, color=TEXT_WHITE):
    """Draw a smooth antialiased home house icon."""
    dim = size * 2 + 4
    ico = get_smooth_icon("home", dim, color)
    surf.blit(ico, (cx - dim // 2, cy - dim // 2))


def draw_smooth_gem(surf, cx, cy, radius=9, color=RUBY_RED):
    """Draw a smooth antialiased player gem badge."""
    dim = radius * 2 + 2
    ico = get_smooth_icon("gem", dim, color)
    surf.blit(ico, (cx - dim // 2, cy - dim // 2))


# ==============================================================================
# Pre-rendered Graphics
# ==============================================================================

def shade(color, factor):
    """Return a lighter (factor > 1) or darker (factor < 1) version of a color."""
    return tuple(max(0, min(255, int(v * factor))) for v in color)


def cell_center(r, c):
    """Pixel center of the cell at board row r, column c."""
    return (BOARD_RECT.x + c * SQUARE + SQUARE // 2,
            BOARD_RECT.y + r * SQUARE + SQUARE // 2)


def column_at(x):
    """Board column (0..COLS-1) under pixel x, or None if x is outside the board."""
    col = (x - PAD_X) // SQUARE
    return col if 0 <= col < COLS else None


def get_desktop_resolution():
    """Return primary display resolution safely across platforms."""
    try:
        sizes = pygame.display.get_desktop_sizes()
        if sizes and len(sizes) > 0:
            return sizes[0]
    except Exception:
        pass
    try:
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return (info.current_w, info.current_h)
    except Exception:
        pass
    return (1920, 1080)


def make_background(total_w=WIDTH, total_h=HEIGHT):
    """Build the vertical gradient with subtle atmospheric depth."""
    surf = pygame.Surface((total_w, total_h))
    for y in range(total_h):
        t = y / total_h
        color = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        pygame.draw.line(surf, color, (0, y), (total_w, y))

    # Ambient top glow over the board
    glow = pygame.Surface((total_w, min(300, total_h)), pygame.SRCALPHA)
    cx, cy = total_w // 2, 0
    for r in range(300, 0, -16):
        alpha = int(16 * (1.0 - r / 300))
        pygame.draw.ellipse(glow, (60, 90, 200, alpha),
                            (cx - r * 1.5, cy - r // 2, r * 3, r))
    surf.blit(glow, (0, 0))
    return surf


def make_disc(color):
    """Pre-render one 3D Polished Ceramic disc."""
    size = RADIUS * 2 * SS
    big = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    r = RADIUS * SS

    # Base rim shadow
    pygame.draw.circle(big, shade(color, 0.45), (c, c), r)

    # Offset highlights
    layers = 16
    for i in range(layers):
        factor = 0.65 + 0.55 * (i / layers)
        layer_color = shade(color, factor)
        lr = int(r * (1.0 - 0.05 * i))
        shift_x = int(c - (r * 0.18 * (i / layers)))
        shift_y = int(c - (r * 0.18 * (i / layers)))
        pygame.draw.circle(big, layer_color, (shift_x, shift_y), lr)

    # Specular gloss glint
    glint_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    glint_rect = pygame.Rect(0, 0, int(r * 0.45), int(r * 0.24))
    glint_rect.center = (int(c - r * 0.35), int(c - r * 0.35))
    pygame.draw.ellipse(glint_surf, (255, 255, 255, 210), glint_rect)
    glint_surf = pygame.transform.rotate(glint_surf, 35)
    gw, gh = glint_surf.get_size()
    big.blit(glint_surf, (c - gw // 2 - int(r * 0.22), c - gh // 2 - int(r * 0.22)))

    # Outer ambient rim
    rim_color = shade(color, 1.25) + (110,)
    rim_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(rim_surf, rim_color, (c, c), int(r * 0.94), width=max(1, int(2 * SS)))
    big.blit(rim_surf, (0, 0))

    return pygame.transform.smoothscale(big, (RADIUS * 2, RADIUS * 2))


def make_board_overlay():
    """Pre-render the sleek midnight board with countersunk 3D sockets."""
    w, h = BOARD_RECT.size
    big = pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)

    pygame.draw.rect(big, BOARD_BASE, (0, 0, w * SS, h * SS), border_radius=24 * SS)
    pygame.draw.rect(big, BOARD_LIP, (0, 0, w * SS, 6 * SS),
                      border_top_left_radius=24 * SS, border_top_right_radius=24 * SS)

    for r in range(ROWS):
        for c in range(COLS):
            cx = (c * SQUARE + SQUARE // 2) * SS
            cy = (r * SQUARE + SQUARE // 2) * SS
            pygame.draw.circle(big, HOLE_SHADOW, (cx, cy - int(3 * SS)), (RADIUS + 4) * SS)
            pygame.draw.circle(big, (0, 0, 0, 0), (cx, cy), RADIUS * SS)
            lip_rect = pygame.Rect(cx - (RADIUS + 2) * SS, cy - (RADIUS + 2) * SS,
                                   (RADIUS + 2) * 2 * SS, (RADIUS + 2) * 2 * SS)
            pygame.draw.arc(big, HOLE_RIM, lip_rect, math.pi * 1.05, math.pi * 1.95,
                            max(1, int(2.5 * SS)))

    pygame.draw.rect(big, BOARD_BORDER, (0, 0, w * SS, h * SS), width=int(2.5 * SS),
                     border_radius=24 * SS)
    return pygame.transform.smoothscale(big, (w, h))


def draw_spotlight(screen, col):
    """Draw a soft vertical spotlight beam through the currently hovered column."""
    if col is None or not (0 <= col < COLS):
        return
    bx = PAD_X + col * SQUARE
    beam_w = SQUARE
    beam_h = ROWS * SQUARE + HOVER_H
    beam = pygame.Surface((beam_w, beam_h), pygame.SRCALPHA)
    for y in range(beam_h):
        t = y / beam_h
        alpha = int(28 * (1.0 - t * 0.7))
        pygame.draw.line(beam, (75, 120, 255, alpha), (4, y), (beam_w - 4, y))
    screen.blit(beam, (bx, HOVER_Y - RADIUS))


# ==============================================================================
# Header & Scoreboard Rendering
# ==============================================================================

def draw_scoreboard(screen, board, fonts, human_turn, K, show_tree, mouse_pos, last_info=None, is_fs=False):
    """
    Unified 2-tier top header strip with generous spacing and Fullscreen toggle.
    Tier 1: Spacious [YOU <score>] pill, [YOUR TURN] capsule, and [<score> AI] pill.
    Tier 2: [search depth K] on left, and crisp action buttons [FULLSCREEN], [RESET] and [TREE] on right.
    Returns dict of button rects for click collision.
    """
    win_w = screen.get_width()
    buttons = {}

    # Header bar background spanning full window width
    header_rect = pygame.Rect(0, 0, win_w, SCORE_H)
    pygame.draw.rect(screen, (15, 19, 38), header_rect)
    pygame.draw.line(screen, (34, 46, 88), (0, SCORE_H - 1), (win_w, SCORE_H - 1), 1)

    human_fours, computer_fours = get_scores(board)

    # -------------------------------------------------------------
    # BOARD SIDE (x = 0 .. WIDTH = 710)
    # -------------------------------------------------------------

    # TIER 1: Player Capsules
    # 1. Left Pill: Human Player
    pill_w, pill_h = 142, 40
    pill_y = 12
    human_pill = pygame.Rect(PAD_X, pill_y, pill_w, pill_h)
    pygame.draw.rect(screen, (22, 28, 56), human_pill, border_radius=20)
    border_color = RUBY_RED if human_turn else (45, 55, 95)
    pygame.draw.rect(screen, border_color, human_pill, width=2 if human_turn else 1, border_radius=20)

    dot_x = PAD_X + 22
    mid_y1 = pill_y + pill_h // 2
    draw_smooth_gem(screen, dot_x, mid_y1, 9, RUBY_RED)
    score_surf = fonts["font"].render(f"YOU  {human_fours}", True, TEXT_WHITE)
    screen.blit(score_surf, (dot_x + 16, mid_y1 - score_surf.get_height() // 2))

    # 2. Center Capsule: Turn status
    center_w, center_h = 180, 38
    center_x = (WIDTH - center_w) // 2
    center_rect = pygame.Rect(center_x, pill_y + 1, center_w, center_h)
    pygame.draw.rect(screen, (18, 24, 48), center_rect, border_radius=19)
    pygame.draw.rect(screen, (45, 58, 102), center_rect, width=1, border_radius=19)

    dots = ""
    if is_full(board):
        status_txt, status_col = "GAME OVER", TEXT_WHITE
    elif human_turn:
        status_txt, status_col = "YOUR TURN", RUBY_RED
    else:
        status_txt, status_col = "AI THINKING", AMBER_GOLD
        dots = "." * (1 + (pygame.time.get_ticks() // 350) % 3)

    status_surf = fonts["small"].render(status_txt, True, status_col)
    status_pos = status_surf.get_rect(center=center_rect.center)
    screen.blit(status_surf, status_pos)
    if dots:
        screen.blit(fonts["small"].render(dots, True, status_col), (status_pos.right + 2, status_pos.y))

    # 3. Right Pill: Computer AI
    comp_x = WIDTH - PAD_X - pill_w
    comp_pill = pygame.Rect(comp_x, pill_y, pill_w, pill_h)
    pygame.draw.rect(screen, (22, 28, 56), comp_pill, border_radius=20)
    ai_border = AMBER_GOLD if not human_turn and not is_full(board) else (45, 55, 95)
    pygame.draw.rect(screen, ai_border, comp_pill, width=2 if not human_turn and not is_full(board) else 1, border_radius=20)

    ai_score_surf = fonts["font"].render(f"{computer_fours}  AI", True, TEXT_WHITE)
    screen.blit(ai_score_surf, (comp_x + 20, mid_y1 - ai_score_surf.get_height() // 2))
    ai_dot_x = comp_x + pill_w - 22
    draw_smooth_gem(screen, ai_dot_x, mid_y1, 9, AMBER_GOLD)

    # TIER 2: Secondary Bar (y = 60)
    # Search Depth Indicator on left
    k_surf = fonts["tiny"].render(f"search depth K = {K}", True, (135, 148, 185))
    screen.blit(k_surf, (PAD_X + 4, 66))

    # Action Buttons on right
    if not show_tree:
        btn_y2 = 58
        home_btn = pygame.Rect(WIDTH - PAD_X - 422, btn_y2, 94, 28)
        fs_btn = pygame.Rect(WIDTH - PAD_X - 322, btn_y2, 100, 28)
        reset_btn = pygame.Rect(WIDTH - PAD_X - 216, btn_y2, 100, 28)
        tree_btn = pygame.Rect(WIDTH - PAD_X - 108, btn_y2, 108, 28)

        # Draw Home button
        hov_h = home_btn.collidepoint(mouse_pos)
        h_bg = (36, 46, 84) if hov_h else (22, 28, 56)
        pygame.draw.rect(screen, h_bg, home_btn, border_radius=6)
        pygame.draw.rect(screen, (80, 105, 180) if hov_h else (48, 62, 115), home_btn, width=1, border_radius=6)
        draw_icon_home(screen, home_btn.x + 15, home_btn.centery, size=5, color=TEXT_WHITE if hov_h else (210, 220, 245))
        lbl_h = fonts["tiny"].render("HOME [H]", True, TEXT_WHITE if hov_h else (210, 220, 245))
        screen.blit(lbl_h, (home_btn.x + 26, home_btn.centery - lbl_h.get_height() // 2))
        buttons["home"] = home_btn

        # Draw Fullscreen button
        hov_f = fs_btn.collidepoint(mouse_pos)
        f_bg = (36, 46, 84) if hov_f else (22, 28, 56)
        pygame.draw.rect(screen, f_bg, fs_btn, border_radius=6)
        pygame.draw.rect(screen, (80, 105, 180) if hov_f else (48, 62, 115), fs_btn, width=1, border_radius=6)
        draw_icon_fullscreen(screen, fs_btn.x + 15, fs_btn.centery, size=5, is_fs=is_fs, color=TEXT_WHITE if hov_f else (210, 220, 245))
        lbl_f = fonts["tiny"].render("WIN [F11]" if is_fs else "FULL [F11]", True, TEXT_WHITE if hov_f else (210, 220, 245))
        screen.blit(lbl_f, (fs_btn.x + 26, fs_btn.centery - lbl_f.get_height() // 2))
        buttons["fullscreen"] = fs_btn

        # Draw Reset button
        hov_r = reset_btn.collidepoint(mouse_pos)
        r_bg = (36, 46, 84) if hov_r else (22, 28, 56)
        pygame.draw.rect(screen, r_bg, reset_btn, border_radius=6)
        pygame.draw.rect(screen, (80, 105, 180) if hov_r else (48, 62, 115), reset_btn, width=1, border_radius=6)
        draw_icon_reset(screen, reset_btn.x + 16, reset_btn.centery, radius=5, color=TEXT_WHITE if hov_r else (210, 220, 245))
        lbl_r = fonts["tiny"].render("RESET [R]", True, TEXT_WHITE if hov_r else (210, 220, 245))
        screen.blit(lbl_r, (reset_btn.x + 27, reset_btn.centery - lbl_r.get_height() // 2))
        buttons["reset"] = reset_btn

        # Draw Tree button
        hov_t = tree_btn.collidepoint(mouse_pos)
        t_bg = (52, 42, 16) if hov_t else (26, 32, 60)
        pygame.draw.rect(screen, t_bg, tree_btn, border_radius=6)
        pygame.draw.rect(screen, AMBER_GOLD if hov_t else (70, 90, 155), tree_btn, width=1, border_radius=6)
        lbl_t = fonts["tiny"].render("TREE [T]", True, AMBER_GOLD if hov_t else TEXT_WHITE)
        screen.blit(lbl_t, (tree_btn.x + 14, tree_btn.centery - lbl_t.get_height() // 2))
        draw_icon_triangle(screen, tree_btn.right - 16, tree_btn.centery, size=4, direction="right", color=AMBER_GOLD if hov_t else TEXT_WHITE)
        buttons["tree"] = tree_btn

    # -------------------------------------------------------------
    # TREE SIDE (when tree is open, x = WIDTH .. win_w)
    # -------------------------------------------------------------
    if show_tree:
        pygame.draw.line(screen, (38, 50, 96), (WIDTH, 0), (WIDTH, SCORE_H), 1)

        title_surf = fonts["font"].render("DECISION TREE", True, TEXT_WHITE)
        screen.blit(title_surf, (WIDTH + 18, 16))

        btn_y = 15
        home_rect = pygame.Rect(win_w - PAD_X - 396, btn_y, 90, 32)
        fs_rect = pygame.Rect(win_w - PAD_X - 300, btn_y, 94, 32)
        reset_rect = pygame.Rect(win_w - PAD_X - 200, btn_y, 98, 32)
        close_rect = pygame.Rect(win_w - PAD_X - 96, btn_y, 96, 32)

        # Home button
        hov_h = home_rect.collidepoint(mouse_pos)
        h_bg = (36, 46, 84) if hov_h else (22, 28, 56)
        pygame.draw.rect(screen, h_bg, home_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 105, 180) if hov_h else (48, 62, 115), home_rect, width=1, border_radius=8)
        draw_icon_home(screen, home_rect.x + 15, home_rect.centery, size=5, color=TEXT_WHITE if hov_h else (210, 220, 245))
        lbl_h = fonts["tiny"].render("HOME [H]", True, TEXT_WHITE if hov_h else (210, 220, 245))
        screen.blit(lbl_h, (home_rect.x + 26, home_rect.centery - lbl_h.get_height() // 2))
        buttons["home"] = home_rect

        # Fullscreen button
        hov_f = fs_rect.collidepoint(mouse_pos)
        f_bg = (36, 46, 84) if hov_f else (22, 28, 56)
        pygame.draw.rect(screen, f_bg, fs_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 105, 180) if hov_f else (48, 62, 115), fs_rect, width=1, border_radius=8)
        draw_icon_fullscreen(screen, fs_rect.x + 15, fs_rect.centery, size=5, is_fs=is_fs, color=TEXT_WHITE if hov_f else (210, 220, 245))
        lbl_f = fonts["tiny"].render("WIN [F11]" if is_fs else "FULL [F11]", True, TEXT_WHITE if hov_f else (210, 220, 245))
        screen.blit(lbl_f, (fs_rect.x + 26, fs_rect.centery - lbl_f.get_height() // 2))
        buttons["fullscreen"] = fs_rect

        # Reset button
        hov_r = reset_rect.collidepoint(mouse_pos)
        r_bg = (36, 46, 84) if hov_r else (22, 28, 56)
        pygame.draw.rect(screen, r_bg, reset_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 105, 180) if hov_r else (48, 62, 115), reset_rect, width=1, border_radius=8)
        draw_icon_reset(screen, reset_rect.x + 15, reset_rect.centery, radius=5, color=TEXT_WHITE if hov_r else (210, 220, 245))
        lbl_r = fonts["tiny"].render("RESET [R]", True, TEXT_WHITE if hov_r else (210, 220, 245))
        screen.blit(lbl_r, (reset_rect.x + 26, reset_rect.centery - lbl_r.get_height() // 2))
        buttons["reset"] = reset_rect

        # Close Tree button
        hov_c = close_rect.collidepoint(mouse_pos)
        c_bg = (52, 26, 32) if hov_c else (32, 22, 38)
        pygame.draw.rect(screen, c_bg, close_rect, border_radius=8)
        pygame.draw.rect(screen, RUBY_RED if hov_c else (85, 45, 65), close_rect, width=1, border_radius=8)
        draw_icon_cross(screen, close_rect.x + 15, close_rect.centery, size=5, color=RUBY_RED if hov_c else (230, 180, 190))
        lbl_c = fonts["tiny"].render("CLOSE [T]", True, TEXT_WHITE if hov_c else (225, 200, 210))
        screen.blit(lbl_c, (close_rect.x + 26, close_rect.centery - lbl_c.get_height() // 2))
        buttons["tree"] = close_rect

        if last_info:
            sub = (f"AI move #{last_info['move']}  |  chose col {last_info['col']}  |  "
                   f"{last_info['nodes']:,} nodes, {last_info['pruned']:,} cut")
            screen.blit(fonts["tiny"].render(sub, True, (140, 155, 195)), (WIDTH + 20, 62))
        else:
            screen.blit(fonts["tiny"].render("Minimax search tree will appear after the computer moves.", True, (120, 135, 175)), (WIDTH + 20, 62))

    return buttons


# ==============================================================================
# Game Board Drawing
# ==============================================================================

def draw_game(screen, board, background, overlay, discs, hover_x=None, hover_player=HUMAN,
              falling=None, hovered_col=None, highlight=()):
    """Draw one complete frame of the game board in layered depth order."""
    screen.blit(background, (0, 0))

    if hovered_col is not None and falling is None:
        draw_spotlight(screen, hovered_col)

    if hover_x is not None and falling is None:
        t = pygame.time.get_ticks() * 0.004
        bob_y = HOVER_Y + math.sin(t) * 3.5
        screen.blit(discs[hover_player], (int(hover_x) - RADIUS, int(bob_y) - RADIUS))
        arrow_ico = get_smooth_icon("hover_arrow", 16, (200, 220, 255, 180))
        screen.blit(arrow_ico, (int(hover_x) - 8, int(bob_y) + RADIUS + 5))

    pygame.draw.rect(screen, HOLE_BACK, BOARD_RECT, border_radius=24)

    win_ring = get_smooth_icon("ring", (RADIUS - 2) * 2, (255, 255, 255))
    ring_offset = RADIUS - 2

    for r in range(ROWS):
        for c in range(COLS):
            p = board[r][c]
            if p != EMPTY:
                x, y = cell_center(r, c)
                screen.blit(discs[p], (x - RADIUS, y - RADIUS))
                if (r, c) in highlight:
                    screen.blit(win_ring, (x - ring_offset, y - ring_offset))

    if falling is not None:
        fx, fy, player = falling
        screen.blit(discs[player], (int(fx) - RADIUS, int(fy) - RADIUS))

    screen.blit(overlay, BOARD_RECT.topleft)


def draw_game_over(screen, board, fonts, mouse_pos):
    """Compact result banner with a tactile Play Again button."""
    human, computer = get_scores(board)
    w = winner(board)
    if w == HUMAN:
        title, accent = "VICTORY! You won the game", RUBY_RED
    elif w == COMPUTER:
        title, accent = "AI WINS this round", AMBER_GOLD
    else:
        title, accent = "IT'S A DRAW", (110, 180, 255)

    card = pygame.Rect(PAD_X, SCORE_H + 8, WIDTH - 2 * PAD_X, HOVER_H - 14)
    pygame.draw.rect(screen, (20, 26, 54), card, border_radius=18)
    pygame.draw.rect(screen, accent, card, width=3, border_radius=18)

    title_surf = fonts["font"].render(title, True, accent)
    screen.blit(title_surf, (card.x + 22, card.y + 14))

    info = f"Score: YOU {human} - {computer} AI"
    screen.blit(fonts["small"].render(info, True, (210, 218, 245)), (card.x + 22, card.y + 42))

    # Action buttons: [HOME [H]] and [PLAY AGAIN [R]]
    play_btn = pygame.Rect(card.right - 146, card.centery - 18, 134, 36)
    hov_p = play_btn.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (40, 52, 98) if hov_p else (28, 36, 72), play_btn, border_radius=10)
    pygame.draw.rect(screen, AMBER_GOLD if hov_p else (70, 90, 160), play_btn, width=2 if hov_p else 1, border_radius=10)
    lbl_p = fonts["small"].render("PLAY AGAIN [R]", True, TEXT_WHITE)
    screen.blit(lbl_p, lbl_p.get_rect(center=play_btn.center))

    home_btn = pygame.Rect(card.right - 256, card.centery - 18, 102, 36)
    hov_h = home_btn.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (40, 52, 98) if hov_h else (28, 36, 72), home_btn, border_radius=10)
    pygame.draw.rect(screen, (80, 105, 180) if hov_h else (50, 65, 120), home_btn, width=2 if hov_h else 1, border_radius=10)
    draw_icon_home(screen, home_btn.x + 16, home_btn.centery, size=5, color=TEXT_WHITE if hov_h else (210, 220, 245))
    lbl_h = fonts["small"].render("HOME [H]", True, TEXT_WHITE)
    screen.blit(lbl_h, (home_btn.x + 28, home_btn.centery - lbl_h.get_height() // 2))

    return play_btn, home_btn


def format_time(seconds):
    """Milliseconds below one second, otherwise seconds."""
    return f"{seconds * 1000:.0f} ms" if seconds < 1 else f"{seconds:.2f} s"


def draw_stats(screen, history, thinking, fonts):
    """
    Stats strip under the board: 5 evenly-spaced metric tiles with clear vertical
    separators, plus running totals underneath.
    """
    rect = STATS_RECT
    pygame.draw.rect(screen, (18, 24, 48), rect, border_radius=16)
    pygame.draw.rect(screen, (42, 56, 108), rect, width=1, border_radius=16)

    last = history[-1] if history else None
    if thinking:
        cells = [("AI MOVE", "thinking...", AMBER_GOLD)] + [
            (n, "...", TEXT_MUTED) for n in ("VALUE", "NODES", "TIME", "PRUNED")
        ]
    elif last:
        cells = [
            ("AI MOVE", f"#{last['move']}  col {last['col']}", AMBER_GOLD),
            ("VALUE", f"{last['value']}", TEXT_WHITE),
            ("NODES", f"{last['nodes']:,}", TEXT_WHITE),
            ("TIME", format_time(last["time"]), TEXT_WHITE),
            ("PRUNED", "-" if last["pruned"] is None else f"{last['pruned']:,}", TEXT_WHITE)
        ]
    else:
        cells = [(n, "-", TEXT_MUTED) for n in ("AI MOVE", "VALUE", "NODES", "TIME", "PRUNED")]

    col_w = (rect.width - 24) // 5
    for i, (label, value, color) in enumerate(cells):
        tile_x = rect.x + 12 + i * col_w
        if i > 0:
            pygame.draw.line(screen, (32, 42, 80), (tile_x - 4, rect.y + 12),
                             (tile_x - 4, rect.y + 52), 1)
        screen.blit(fonts["tiny"].render(label, True, TEXT_MUTED), (tile_x, rect.y + 10))
        screen.blit(fonts["small"].render(value, True, color), (tile_x, rect.y + 30))

    if history:
        total_nodes = sum(h["nodes"] for h in history)
        total_time = sum(h["time"] for h in history)
        pruned_list = [h["pruned"] for h in history if h.get("pruned") is not None]
        total_pruned = sum(pruned_list)
        footer = (f"Totals ({len(history)} AI moves): {total_nodes:,} nodes, "
                  f"{format_time(total_time)}, {total_pruned:,} pruned | avg {total_nodes // len(history):,} nodes/move")
    else:
        footer = "AI performance stats will appear here after the computer's first move."
    screen.blit(fonts["tiny"].render(footer, True, (130, 142, 178)), (rect.x + 16, rect.bottom - 24))


# ==============================================================================
# Decision Tree & Integrated Node Inspector Panel
# ==============================================================================

class TreePanel:
    """
    Scrollable, collapsible view of the minimax tree plus an integrated
    Node Inspector Card that displays selected node metrics, evaluation rationale,
    and a mini-board simulation.
    """

    ROW_H = 28
    BUTTONS = ("Expand All", "Collapse All", "Chosen Path")

    def __init__(self):
        self.root = None
        self.info = None
        self.expanded = set()
        self.path = set()
        self.rows = []
        self.scroll = 0
        self.selected_node = None
        self.hovered_row = None
        self.active_button_idx = 2

    def clear(self):
        self.root, self.info, self.rows = None, None, []
        self.expanded, self.path, self.scroll = set(), set(), 0
        self.selected_node = None

    def set_tree(self, root, info):
        self.root, self.info = root, info
        self.path = set(principal_path(root))
        self.expanded = default_expanded(root)
        self.selected_node = root
        self.scroll = 0
        self._refresh()

    def _refresh(self):
        self.rows = visible_rows(self.root, self.expanded) if self.root else []
        self.scroll = max(0, min(self.scroll, self._max_scroll()))

    def _list_rect(self, rect):
        # Upper portion: scrollable tree list
        return pygame.Rect(rect.x + 16, rect.y + 54, rect.width - 32, 380)

    def _inspector_rect(self, rect):
        # Lower portion: Node Inspector Card
        list_r = self._list_rect(rect)
        top = list_r.bottom + 12
        return pygame.Rect(rect.x + 16, top, rect.width - 32, rect.bottom - top - 14)

    def _max_scroll(self):
        return max(0, len(self.rows) * self.ROW_H - self._list_rect(PANEL_RECT).height)

    def _button_rects(self, rect):
        w, gap = 126, 10
        return [pygame.Rect(rect.x + 16 + i * (w + gap), rect.y + 12, w, 32)
                for i in range(len(self.BUTTONS))]

    def scroll_by(self, pixels):
        self.scroll = max(0, min(self.scroll + pixels, self._max_scroll()))

    def click(self, pos, rect):
        """Handle clicks inside the panel: toolbar buttons or rows."""
        if self.root is None:
            return
        for i, button in enumerate(self._button_rects(rect)):
            if button.collidepoint(pos):
                self.active_button_idx = i
                if i == 0:
                    self.expanded = expand_all(self.root)
                elif i == 1:
                    self.expanded = {self.root}
                else:
                    self.expanded = default_expanded(self.root)
                self.scroll = 0
                self._refresh()
                return

        area = self._list_rect(rect)
        if area.collidepoint(pos):
            index = (pos[1] - area.y + self.scroll) // self.ROW_H
            if 0 <= index < len(self.rows):
                node, has_children, is_open = self.rows[index]
                self.selected_node = node
                if has_children:
                    (self.expanded.discard if is_open else self.expanded.add)(node)
                    self._refresh()

    def update_hover(self, pos, rect):
        """Track hovered row for visual highlight."""
        area = self._list_rect(rect)
        if area.collidepoint(pos):
            index = (pos[1] - area.y + self.scroll) // self.ROW_H
            self.hovered_row = index if 0 <= index < len(self.rows) else None
        else:
            self.hovered_row = None

    def draw(self, screen, rect, fonts, mouse_pos):
        """Draw the tree view, toolbar, scrollable rows, and Inspector Card."""
        pygame.draw.rect(screen, (11, 14, 28), rect)
        pygame.draw.line(screen, (38, 50, 96), rect.topleft, rect.bottomleft, 2)

        if self.root is None:
            msg = fonts["font"].render("DECISION TREE & INSPECTOR", True, TEXT_WHITE)
            screen.blit(msg, (rect.x + 18, rect.y + 24))
            hint = fonts["small"].render("Minimax search tree will appear after the AI moves.",
                                         True, TEXT_MUTED)
            screen.blit(hint, (rect.x + 18, rect.y + 60))
            return

        # 1. Action Toolbar buttons
        for idx, (label, button) in enumerate(zip(self.BUTTONS, self._button_rects(rect))):
            hov = button.collidepoint(mouse_pos)
            active = (idx == self.active_button_idx)
            bg = (46, 38, 18) if active else ((32, 42, 78) if hov else (20, 26, 52))
            border = AMBER_GOLD if active else ((75, 95, 170) if hov else (45, 58, 105))
            pygame.draw.rect(screen, bg, button, border_radius=6)
            pygame.draw.rect(screen, border, button, width=2 if (active or hov) else 1, border_radius=6)

            btn_col = AMBER_GOLD if active else (TEXT_WHITE if hov else (200, 210, 235))
            if idx == 0:
                draw_icon_triangle(screen, button.x + 14, button.centery, size=4, direction="down", color=btn_col)
                text = fonts["tiny"].render(label, True, btn_col)
                screen.blit(text, (button.x + 24, button.centery - text.get_height() // 2))
            elif idx == 1:
                draw_icon_triangle(screen, button.x + 14, button.centery, size=4, direction="up", color=btn_col)
                text = fonts["tiny"].render(label, True, btn_col)
                screen.blit(text, (button.x + 24, button.centery - text.get_height() // 2))
            else:
                draw_icon_star(screen, button.x + 14, button.centery, r=6, color=btn_col)
                text = fonts["tiny"].render(label, True, btn_col)
                screen.blit(text, (button.x + 24, button.centery - text.get_height() // 2))

        # 2. Tree List View area
        area = self._list_rect(rect)
        pygame.draw.rect(screen, (15, 20, 40), area, border_radius=10)
        pygame.draw.rect(screen, (34, 46, 90), area, width=1, border_radius=10)

        old_clip = screen.get_clip()
        screen.set_clip(area)
        first = self.scroll // self.ROW_H
        count = area.height // self.ROW_H + 2
        for n in range(first, min(first + count, len(self.rows))):
            self._draw_row(screen, area, n, fonts)
        screen.set_clip(old_clip)

        # Scrollbar thumb
        if self._max_scroll() > 0:
            track = pygame.Rect(area.right - 8, area.y + 4, 5, area.height - 8)
            thumb_h = max(30, area.height * area.height // (len(self.rows) * self.ROW_H))
            thumb_y = area.y + 4 + (area.height - 8 - thumb_h) * self.scroll // self._max_scroll()
            pygame.draw.rect(screen, (24, 32, 64), track, border_radius=3)
            pygame.draw.rect(screen, (85, 105, 175), (track.x, thumb_y, 5, thumb_h), border_radius=3)

        # 3. Node Inspector Card (lower panel)
        self._draw_inspector(screen, rect, fonts)

    def _draw_row(self, screen, area, n, fonts):
        """Draw one row of the tree with badge chips, bounds, and hover effect."""
        node, has_children, is_open = self.rows[n]
        y = area.y + n * self.ROW_H - self.scroll
        row_rect = pygame.Rect(area.x + 2, y, area.width - 12, self.ROW_H - 2)

        on_path = node in self.path
        is_selected = (node == self.selected_node)
        is_hovered = (n == self.hovered_row)

        if is_selected:
            pygame.draw.rect(screen, (48, 42, 18), row_rect, border_radius=6)
            pygame.draw.rect(screen, AMBER_GOLD, row_rect, width=1, border_radius=6)
        elif on_path:
            pygame.draw.rect(screen, (36, 32, 16), row_rect, border_radius=6)
            pygame.draw.rect(screen, (160, 130, 40), (row_rect.x, row_rect.y, 3, row_rect.height), border_radius=2)
        elif is_hovered:
            pygame.draw.rect(screen, (24, 32, 62), row_rect, border_radius=6)

        x = area.x + 10 + node.depth * 16
        mid = y + self.ROW_H // 2 - 1

        # Expansion arrow
        if has_children:
            draw_icon_triangle(screen, x + 4, mid, size=4, direction="down" if is_open else "right",
                               color=PRUNED_GREY if node.pruned else (160, 175, 215))
        x += 16

        # Badge pill for node type
        if node.is_leaf:
            badge_txt = "LEAF"
            badge_bg = (18, 45, 30) if not node.pruned else (26, 30, 42)
            badge_col = FINAL_BLUE if node.final else LEAF_GREEN
        elif node.kind == "MAX":
            badge_txt = "MAX"
            badge_bg = (48, 38, 12) if not node.pruned else (26, 30, 42)
            badge_col = AMBER_GOLD if not node.pruned else PRUNED_GREY
        else:
            badge_txt = "MIN"
            badge_bg = (48, 20, 26) if not node.pruned else (26, 30, 42)
            badge_col = (255, 120, 140) if not node.pruned else PRUNED_GREY

        badge_w, badge_h = 40, 19
        badge_rect = pygame.Rect(x, mid - badge_h // 2, badge_w, badge_h)
        pygame.draw.rect(screen, badge_bg, badge_rect, border_radius=4)
        b_surf = fonts["tiny"].render(badge_txt, True, badge_col)
        screen.blit(b_surf, b_surf.get_rect(center=badge_rect.center))
        x += badge_w + 8

        # Move text
        label_str = node_label(node).replace("[MAX]", "").replace("[MIN]", "").replace("[LEAF]", "").strip()
        label_surf = fonts["row"].render(label_str, True, TEXT_WHITE if on_path else (190, 205, 235))
        screen.blit(label_surf, (x, y + 4))

        if node.pruned:
            pygame.draw.line(screen, PRUNED_GREY, (x, mid), (x + label_surf.get_width(), mid), 1)

        details = f"α={fmt_bound(node.alpha)}  β={fmt_bound(node.beta)}  {node_tail(node)}"
        detail_col = PRUNED_GREY if node.pruned else (TEXT_WHITE if on_path else (150, 165, 200))
        screen.blit(fonts["row"].render(details, True, detail_col), (x + label_surf.get_width() + 12, y + 4))

    def _draw_inspector(self, screen, rect, fonts):
        """Draw the lower Node Inspector Card with metrics and simulated mini-board."""
        card = self._inspector_rect(rect)
        pygame.draw.rect(screen, (16, 22, 46), card, border_radius=12)
        pygame.draw.rect(screen, (40, 56, 110), card, width=1, border_radius=12)

        node = self.selected_node or self.root
        if not node:
            return

        draw_icon_search(screen, card.x + 22, card.y + 20, r=6, color=AMBER_GOLD)
        icon_title = fonts["small"].render("NODE INSPECTOR", True, AMBER_GOLD)
        screen.blit(icon_title, (card.x + 36, card.y + 12))

        if node.depth == 0:
            ident = "Root State (Computer's Turn)"
        else:
            p_name = "AI (MAX)" if node.kind == "MIN" else "Human (MIN)"
            ident = f"Move: Column {node.col + 1} by {p_name} at Depth {node.depth}"
        screen.blit(fonts["tiny"].render(ident, True, TEXT_WHITE), (card.x + 16, card.y + 34))

        metrics = [
            ("TYPE", "LEAF" if node.is_leaf else node.kind, LEAF_GREEN if node.is_leaf else AMBER_GOLD),
            ("ALPHA (α)", fmt_bound(node.alpha), TEXT_WHITE),
            ("BETA (β)", fmt_bound(node.beta), TEXT_WHITE),
            ("EVALUATION", f"{node.value if node.value is not None else '-'}", (120, 210, 255))
        ]
        badge_w = (card.width - 32 - 18) // 4
        by = card.y + 56
        for idx, (label, val, col) in enumerate(metrics):
            bx = card.x + 16 + idx * (badge_w + 6)
            b_rect = pygame.Rect(bx, by, badge_w, 44)
            pygame.draw.rect(screen, (22, 30, 60), b_rect, border_radius=6)
            pygame.draw.rect(screen, (46, 62, 115), b_rect, width=1, border_radius=6)
            screen.blit(fonts["tiny"].render(label, True, TEXT_MUTED), (bx + 8, by + 5))
            screen.blit(fonts["small"].render(val, True, col), (bx + 8, by + 22))

        ey = by + 56
        if node.pruned:
            draw_icon_cut(screen, card.x + 22, ey + 7, size=5, color=(255, 140, 160))
            exp = "PRUNED SUB-TREE: Search cutoff occurred (alpha >= beta). Exploring further would not alter the optimal decision."
            exp_col = (255, 140, 160)
        elif node in self.path:
            draw_icon_star(screen, card.x + 22, ey + 7, r=6, color=AMBER_GOLD)
            exp = "OPTIMAL PATH: This node forms part of the principal variation chosen by Minimax for optimal play."
            exp_col = AMBER_GOLD
        elif node.is_leaf:
            pygame.draw.circle(screen, LEAF_GREEN, (card.x + 22, ey + 7), 4)
            exp = f"LEAF EVALUATION: Position evaluated with heuristic score ({node.value})."
            exp_col = LEAF_GREEN
        else:
            pygame.draw.circle(screen, (190, 205, 235), (card.x + 22, ey + 7), 4)
            exp = f"DECISION NODE: Explored {len(node.children)} candidate counter-moves."
            exp_col = (190, 205, 235)

        exp_surf = fonts["tiny"].render(exp, True, exp_col)
        screen.blit(exp_surf, (card.x + 36, ey))

        # Mini Board Simulation
        if node.board:
            mini_x = card.x + 16
            mini_y = ey + 24
            cell_s = 14
            mini_w = COLS * cell_s + 8
            mini_h = ROWS * cell_s + 8
            mini_rect = pygame.Rect(mini_x, mini_y, mini_w, mini_h)
            pygame.draw.rect(screen, (11, 15, 32), mini_rect, border_radius=6)
            pygame.draw.rect(screen, (36, 48, 92), mini_rect, width=1, border_radius=6)

            for r in range(ROWS):
                for c in range(COLS):
                    val = node.board[r][c]
                    cx = mini_x + 4 + c * cell_s + cell_s // 2
                    cy = mini_y + 4 + r * cell_s + cell_s // 2
                    if val == HUMAN:
                        pygame.draw.circle(screen, RUBY_RED, (cx, cy), 5)
                    elif val == COMPUTER:
                        pygame.draw.circle(screen, AMBER_GOLD, (cx, cy), 5)
                    else:
                        pygame.draw.circle(screen, (22, 28, 52), (cx, cy), 4)

            lbl_m = fonts["tiny"].render("Simulated Board State at this node", True, TEXT_MUTED)
            screen.blit(lbl_m, (mini_rect.right + 14, mini_rect.centery - 6))


# ==============================================================================
# Dropping Animation
# ==============================================================================

def animate_drop(render, col, row, player, current_hover_x=None):
    """Drop a disc with smooth gravity and an elastic landing bounce."""
    x = cell_center(row, col)[0]
    y = float(HOVER_Y)
    target_y = float(cell_center(row, col)[1])
    speed = 2.0
    gravity = 3.2
    bounces = 0
    max_bounces = 2
    clock = pygame.time.Clock()

    while True:
        speed += gravity
        y += speed

        if y >= target_y:
            y = target_y
            if bounces < max_bounces and abs(speed) > 4.5:
                speed = -speed * 0.32
                bounces += 1
            else:
                break

        render(falling=(x, y, player), hover_x=current_hover_x)
        pygame.event.pump()
        clock.tick(60)


def start_ai_job(board, K):
    """Run choose_move in a background thread so the GUI stays responsive."""
    snapshot = [row[:] for row in board]
    job = {"result": None, "error": None}

    def work():
        try:
            job["result"] = choose_move(snapshot, K)
        except Exception as exc:
            job["error"] = exc

    job["thread"] = threading.Thread(target=work, daemon=True)
    job["thread"].start()
    return job


class GameState:
    """Everything that changes during one game."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = new_board()
        self.human_turn = True
        self.computer_move_at = 0
        self.history = []
        self.fours = set()
        self.ai_job = None


# ==============================================================================
# Start Screen (Search Depth K Input)
# ==============================================================================

def draw_start_screen(screen, background, fonts, text, error, mouse_pos, is_fs=False):
    """Clean start screen with clickable depth preset pills and glowing input box."""
    screen.blit(background, (0, 0))
    cx = WIDTH // 2

    # Top right Fullscreen toggle button
    fs_btn = pygame.Rect(WIDTH - PAD_X - 104, 18, 104, 30)
    hov_f = fs_btn.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (36, 46, 84) if hov_f else (22, 28, 56), fs_btn, border_radius=6)
    pygame.draw.rect(screen, (80, 105, 180) if hov_f else (48, 62, 115), fs_btn, width=1, border_radius=6)
    draw_icon_fullscreen(screen, fs_btn.x + 15, fs_btn.centery, size=5, is_fs=is_fs, color=TEXT_WHITE if hov_f else (210, 220, 245))
    lbl_f = fonts["tiny"].render("WIN [F11]" if is_fs else "FULL [F11]", True, TEXT_WHITE if hov_f else (210, 220, 245))
    screen.blit(lbl_f, (fs_btn.x + 26, fs_btn.centery - lbl_f.get_height() // 2))

    title = fonts["big"].render("CONNECT 4", True, TEXT_WHITE)
    screen.blit(title, title.get_rect(center=(cx, 160)))

    sub = fonts["small"].render("MINIMAX AI WITH ALPHA-BETA PRUNING", True, (120, 150, 235))
    screen.blit(sub, sub.get_rect(center=(cx, 210)))

    card_w, card_h = 460, 320
    card = pygame.Rect(cx - card_w // 2, 255, card_w, card_h)
    pygame.draw.rect(screen, (20, 26, 56), card, border_radius=22)
    pygame.draw.rect(screen, (46, 62, 120), card, width=2, border_radius=22)

    prompt = fonts["font"].render("Select Search Depth (K)", True, TEXT_WHITE)
    screen.blit(prompt, prompt.get_rect(center=(cx, card.top + 40)))

    presets = [(2, "K = 2 (Fast)"), (4, "K = 4 (Normal)"), (6, "K = 6 (Deep)")]
    preset_rects = []
    pw = 124
    for idx, (k_val, label) in enumerate(presets):
        px = card.x + 26 + idx * (pw + 14)
        pr = pygame.Rect(px, card.top + 76, pw, 36)
        hov = pr.collidepoint(mouse_pos)
        is_cur = (text == str(k_val))
        bg = (52, 42, 18) if is_cur else ((36, 46, 84) if hov else (24, 32, 62))
        border = AMBER_GOLD if is_cur else ((80, 105, 180) if hov else (48, 62, 115))
        pygame.draw.rect(screen, bg, pr, border_radius=8)
        pygame.draw.rect(screen, border, pr, width=2 if (is_cur or hov) else 1, border_radius=8)
        lbl = fonts["tiny"].render(label, True, AMBER_GOLD if is_cur else TEXT_WHITE)
        screen.blit(lbl, lbl.get_rect(center=pr.center))
        preset_rects.append((pr, k_val))

    or_lbl = fonts["tiny"].render("- or type depth number -", True, TEXT_MUTED)
    screen.blit(or_lbl, or_lbl.get_rect(center=(cx, card.top + 130)))

    box = pygame.Rect(cx - 80, card.top + 150, 160, 54)
    pygame.draw.rect(screen, (12, 16, 36), box, border_radius=12)
    pygame.draw.rect(screen, AMBER_GOLD, box, width=2, border_radius=12)

    cursor = "|" if (pygame.time.get_ticks() // 450) % 2 == 0 else " "
    typed = fonts["font"].render((text or "") + cursor, True, TEXT_WHITE)
    screen.blit(typed, typed.get_rect(center=box.center))

    start_btn = pygame.Rect(cx - 100, card.top + 224, 200, 44)
    hov_start = start_btn.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (58, 46, 16) if hov_start else (42, 34, 14), start_btn, border_radius=10)
    pygame.draw.rect(screen, AMBER_GOLD, start_btn, width=2, border_radius=10)
    btn_col = AMBER_GOLD if hov_start else TEXT_WHITE
    btn_lbl = fonts["small"].render("START GAME", True, btn_col)
    lbl_w = btn_lbl.get_width()
    text_x = start_btn.centerx - (lbl_w + 16) // 2
    screen.blit(btn_lbl, (text_x, start_btn.centery - btn_lbl.get_height() // 2))
    draw_icon_triangle(screen, text_x + lbl_w + 10, start_btn.centery, size=5, direction="right", color=btn_col)

    if error:
        err_s = fonts["tiny"].render(error, True, RUBY_RED)
        screen.blit(err_s, err_s.get_rect(center=(cx, card.bottom - 22)))
    else:
        hint_s = fonts["tiny"].render("Press [F11] for Fullscreen  •  [Esc] to Quit", True, (110, 125, 165))
        screen.blit(hint_s, hint_s.get_rect(center=(cx, card.bottom - 22)))

    return preset_rects, start_btn, fs_btn


def ask_k_screen(screen, background, fonts, initial_k="4", is_fs=False):
    """Prompt the user for depth K with clickable presets or typing, supporting F11 fullscreen."""
    text, error = str(initial_k), ""
    clock = pygame.time.Clock()
    desktop_w, desktop_h = get_desktop_resolution()
    start_canvas = pygame.Surface((WIDTH, HEIGHT))
    bg_full = make_background(total_w=desktop_w, total_h=desktop_h)

    def apply_screen_mode():
        nonlocal screen, bg_full
        if is_fs:
            try:
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except Exception:
                screen = pygame.display.set_mode((desktop_w, desktop_h), pygame.FULLSCREEN)
            sw, sh = screen.get_width(), screen.get_height()
            bg_full = make_background(total_w=max(sw, WIDTH), total_h=max(sh, HEIGHT))
        else:
            screen = pygame.display.set_mode((WIDTH, HEIGHT))

    apply_screen_mode()

    while True:
        sw, sh = screen.get_width(), screen.get_height()
        ox = max(0, (sw - WIDTH) // 2) if is_fs else 0
        oy = max(0, (sh - HEIGHT) // 2) if is_fs else 0
        raw_mpos = pygame.mouse.get_pos()
        mpos = (raw_mpos[0] - ox, raw_mpos[1] - oy)

        preset_rects, start_btn, fs_btn = draw_start_screen(start_canvas, background, fonts, text, error, mpos, is_fs=is_fs)

        if is_fs:
            screen.blit(bg_full, (0, 0))
            screen.blit(start_canvas, (ox, oy))
        else:
            screen.blit(start_canvas, (0, 0))

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    is_fs = not is_fs
                    apply_screen_mode()
                elif event.key == pygame.K_ESCAPE:
                    if is_fs:
                        is_fs = False
                        apply_screen_mode()
                    else:
                        return None, False
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                    error = ""
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if text and text.isdigit() and int(text) >= 1:
                        return int(text), is_fs
                    error = "Please enter depth 1 or higher"
                elif event.unicode.isascii() and event.unicode.isdigit() and len(text) < 2:
                    text += event.unicode
                    error = ""
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                ev_pos = (event.pos[0] - ox, event.pos[1] - oy)
                if fs_btn.collidepoint(ev_pos):
                    is_fs = not is_fs
                    apply_screen_mode()
                elif start_btn.collidepoint(ev_pos):
                    if text and text.isdigit() and int(text) >= 1:
                        return int(text), is_fs
                    error = "Please enter depth 1 or higher"
                for pr, kval in preset_rects:
                    if pr.collidepoint(ev_pos):
                        return kval, is_fs


# ==============================================================================
# Main Application Loop
# ==============================================================================

def main():
    """Main application loop with Fullscreen (F11) and Home screen support."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Connect 4 - Minimax AI Studio")

    face = "segoeui,arial,helvetica"
    fonts = {
        "font": pygame.font.SysFont(face, 24, bold=True),
        "small": pygame.font.SysFont(face, 16, bold=True),
        "tiny": pygame.font.SysFont(face, 13, bold=True),
        "row": pygame.font.SysFont(face, 14),
        "big": pygame.font.SysFont(face, 50, bold=True),
    }

    background = make_background(total_w=WIDTH + PANEL_W)
    overlay = make_board_overlay()
    discs = {p: make_disc(col) for p, col in DISC_COLORS.items()}

    desktop_w, desktop_h = get_desktop_resolution()
    bg_full = make_background(total_w=desktop_w, total_h=desktop_h)
    canvas = pygame.Surface((WIDTH + PANEL_W, HEIGHT))

    state = GameState()
    panel = TreePanel()
    show_tree = False
    smooth_hover_x = WIDTH // 2
    clock = pygame.time.Clock()
    running = True

    res = ask_k_screen(screen, background, fonts, initial_k="4", is_fs=False)
    if res is None or res[0] is None:
        pygame.quit()
        return
    K, is_fullscreen = res

    offset_x, offset_y = 0, 0

    def apply_display_mode():
        nonlocal screen, offset_x, offset_y, bg_full
        cw = WIDTH + (PANEL_W if show_tree else 0)
        if is_fullscreen:
            try:
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except Exception:
                screen = pygame.display.set_mode((desktop_w, desktop_h), pygame.FULLSCREEN)
            sw, sh = screen.get_width(), screen.get_height()
            bg_full = make_background(total_w=max(sw, WIDTH + PANEL_W), total_h=max(sh, HEIGHT))
            offset_x = max(0, (sw - cw) // 2)
            offset_y = max(0, (sh - HEIGHT) // 2)
        else:
            screen = pygame.display.set_mode((cw, HEIGHT))
            offset_x, offset_y = 0, 0

    apply_display_mode()

    def toggle_fullscreen():
        nonlocal is_fullscreen
        is_fullscreen = not is_fullscreen
        apply_display_mode()

    def toggle_tree():
        nonlocal show_tree
        show_tree = not show_tree
        apply_display_mode()

    def go_home():
        nonlocal K, is_fullscreen, running, smooth_hover_x
        state.ai_job = None
        res_k = ask_k_screen(screen, background, fonts, initial_k=str(K), is_fs=is_fullscreen)
        if res_k is None or res_k[0] is None:
            running = False
            return
        K, is_fullscreen = res_k
        state.reset()
        panel.clear()
        smooth_hover_x = WIDTH // 2
        apply_display_mode()

    def render(hover_x=None, falling=None, active_col=None):
        cw = WIDTH + (PANEL_W if show_tree else 0)
        raw_mpos = pygame.mouse.get_pos()
        mouse_pos = (raw_mpos[0] - offset_x, raw_mpos[1] - offset_y)

        draw_game(canvas, state.board, background, overlay, discs,
                  hover_x=hover_x,
                  hover_player=HUMAN if state.human_turn else COMPUTER,
                  falling=falling, hovered_col=active_col, highlight=state.fours)

        buttons = draw_scoreboard(canvas, state.board, fonts, state.human_turn, K,
                                  show_tree, mouse_pos, last_info=panel.info, is_fs=is_fullscreen)
        draw_stats(canvas, state.history, not state.human_turn and not is_full(state.board), fonts)

        play_again_btn, home_btn_over = None, None
        if is_full(state.board):
            play_again_btn, home_btn_over = draw_game_over(canvas, state.board, fonts, mouse_pos)

        if show_tree:
            panel.update_hover(mouse_pos, PANEL_RECT)
            panel.draw(canvas, PANEL_RECT, fonts, mouse_pos)

        sub_canvas = canvas.subsurface((0, 0, cw, HEIGHT))
        if is_fullscreen:
            screen.blit(bg_full, (0, 0))
            screen.blit(sub_canvas, (offset_x, offset_y))
        else:
            screen.blit(sub_canvas, (0, 0))

        pygame.display.flip()
        return buttons, play_again_btn, home_btn_over

    def finish_ai_move():
        job, state.ai_job = state.ai_job, None
        if job["error"] is not None:
            raise job["error"]
        col, stats = job["result"]
        after, row = drop_piece(state.board, col, COMPUTER)
        animate_drop(render, col, row, COMPUTER, current_hover_x=cell_center(0, col)[0])
        state.board = after
        state.fours = four_cells(after)
        state.human_turn = True

        entry = {"move": len(state.history) + 1, "col": col + 1, "K": K,
                 "value": stats["value"], "nodes": stats["nodes"],
                 "time": stats["time"], "pruned": stats["pruned"]}
        state.history.append(entry)
        if stats.get("root") is not None:
            panel.set_tree(stats["root"], entry)
        pygame.event.clear(pygame.MOUSEBUTTONDOWN)

    while running:
        raw_mpos = pygame.mouse.get_pos()
        mouse_x = raw_mpos[0] - offset_x
        mouse_y = raw_mpos[1] - offset_y
        mouse_col = column_at(mouse_x) if (mouse_y >= TOP and mouse_y < BOARD_RECT.bottom and 0 <= mouse_x < WIDTH) else None

        if mouse_col is not None and mouse_col in get_valid_moves(state.board):
            target_x = cell_center(0, mouse_col)[0]
            smooth_hover_x += (target_x - smooth_hover_x) * 0.28
            active_hover_col = mouse_col
        else:
            active_hover_col = None

        buttons, play_again_btn, home_btn_over = render(
            hover_x=smooth_hover_x if state.human_turn and active_hover_col is not None else None,
            active_col=active_hover_col
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                elif event.key == pygame.K_h:
                    go_home()
                elif event.key == pygame.K_ESCAPE:
                    if is_fullscreen:
                        toggle_fullscreen()
                    else:
                        running = False
                elif event.key == pygame.K_t:
                    toggle_tree()
                elif event.key == pygame.K_r:
                    state.reset()
                    panel.clear()
                elif event.unicode in "1234567":
                    col = int(event.unicode) - 1
                    if state.human_turn and col in get_valid_moves(state.board):
                        after, row = drop_piece(state.board, col, HUMAN)
                        animate_drop(render, col, row, HUMAN, current_hover_x=smooth_hover_x)
                        state.board = after
                        state.fours = four_cells(after)
                        state.human_turn = False
                        state.computer_move_at = pygame.time.get_ticks() + 180
            elif event.type == pygame.MOUSEWHEEL:
                ev_x = pygame.mouse.get_pos()[0] - offset_x
                ev_y = pygame.mouse.get_pos()[1] - offset_y
                if show_tree and PANEL_RECT.collidepoint((ev_x, ev_y)):
                    panel.scroll_by(-event.y * TreePanel.ROW_H * 2)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                ev_pos = (event.pos[0] - offset_x, event.pos[1] - offset_y)
                if "home" in buttons and buttons["home"].collidepoint(ev_pos):
                    go_home()
                elif "fullscreen" in buttons and buttons["fullscreen"].collidepoint(ev_pos):
                    toggle_fullscreen()
                elif "reset" in buttons and buttons["reset"].collidepoint(ev_pos):
                    state.reset()
                    panel.clear()
                elif "tree" in buttons and buttons["tree"].collidepoint(ev_pos):
                    toggle_tree()
                elif home_btn_over and home_btn_over.collidepoint(ev_pos):
                    go_home()
                elif play_again_btn and play_again_btn.collidepoint(ev_pos):
                    state.reset()
                    panel.clear()
                elif show_tree and PANEL_RECT.collidepoint(ev_pos):
                    panel.click(ev_pos, PANEL_RECT)
                elif ev_pos[1] >= TOP and ev_pos[1] < BOARD_RECT.bottom and 0 <= ev_pos[0] < WIDTH:
                    col = column_at(ev_pos[0])
                    if state.human_turn and col is not None and col in get_valid_moves(state.board):
                        after, row = drop_piece(state.board, col, HUMAN)
                        animate_drop(render, col, row, HUMAN, current_hover_x=smooth_hover_x)
                        state.board = after
                        state.fours = four_cells(after)
                        state.human_turn = False
                        state.computer_move_at = pygame.time.get_ticks() + 180

        # Computer's turn
        if not state.human_turn and not is_full(state.board):
            if state.ai_job is None:
                if pygame.time.get_ticks() >= state.computer_move_at:
                    state.ai_job = start_ai_job(state.board, K)
            elif not state.ai_job["thread"].is_alive():
                finish_ai_move()

        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
