"""
gui.py - Pygame GUI: human vs. minimax AI, with live AI stats and a toggleable
minimax-tree panel (scrollable, collapsible, chosen path highlighted, pruned
nodes greyed out). Keys: T = show/hide tree, R = play again, Esc = quit.

Layout:
    1. Scoreboard strip with floating player capsules & turn indicators.
    2. Hover & drop zone with column spotlight and smooth floating disc.
    3. The board drawn in depth layers:
       - Background gradient & ambient glow
       - Column spotlight beam
       - Sockets background
       - Discs (with elastic bounce physics)
       - Beveled midnight board overlay with countersunk 3D holes
"""

import math
import threading

import pygame

from ai import choose_move
from engine import (ROWS, COLS, EMPTY, HUMAN, COMPUTER, new_board, four_cells,
                    get_valid_moves, drop_piece, get_scores, is_full, winner)
from tree import fmt_bound, node_label, node_tail
from tree_view import default_expanded, expand_all, principal_path, visible_rows

# ---------- Layout & Geometry ----------
SQUARE = 80                           # pixel size of one cell
PAD_X = 24                            # horizontal margin around the board
SCORE_H = 68                          # height of the top scoreboard bar
HOVER_H = SQUARE                      # height of hover guide zone
TOP = SCORE_H + HOVER_H               # top coordinate of the board
HOVER_Y = SCORE_H + HOVER_H // 2      # resting vertical center for hover disc
RADIUS = SQUARE // 2 - 9              # radius of a hole / disc
WIDTH = COLS * SQUARE + 2 * PAD_X
BOARD_RECT = pygame.Rect(PAD_X, TOP, COLS * SQUARE, ROWS * SQUARE)
STATS_H = 86                          # height of the AI-stats strip under the board
STATS_RECT = pygame.Rect(PAD_X, BOARD_RECT.bottom + 12, WIDTH - 2 * PAD_X, STATS_H)
HEIGHT = STATS_RECT.bottom + 14
PANEL_W = 560                         # width of the tree panel (added to the right)
PANEL_RECT = pygame.Rect(WIDTH, 0, PANEL_W, HEIGHT)
TREE_BUTTON = pygame.Rect(STATS_RECT.right - 100, STATS_RECT.y + 12, 88, 32)

# ---------- Palette: Sleek Midnight Glass ----------
BG_TOP = (18, 22, 44)                 # midnight indigo
BG_BOTTOM = (9, 11, 22)               # deep abyss
BOARD_BASE = (24, 32, 66)             # sleek chassis color
BOARD_BORDER = (46, 62, 118)          # chassis rim highlight
BOARD_LIP = (70, 92, 170)             # top edge highlight
HOLE_BACK = (12, 15, 30)              # deep socket interior
HOLE_SHADOW = (6, 8, 18)              # countersunk top inner shadow
HOLE_RIM = (44, 58, 108)              # bottom rim bevel

# Discs (3D Polished Ceramic / Gem tones)
RUBY_RED = (235, 52, 82)              # Human disc primary
AMBER_GOLD = (250, 188, 38)           # Computer disc primary
TEXT_WHITE = (242, 245, 255)          # primary text
TEXT_MUTED = (145, 155, 190)          # secondary text
PRUNED_GREY = (88, 98, 128)           # greyed-out (pruned) tree rows
LEAF_GREEN = (120, 205, 150)          # heuristic leaves
FINAL_BLUE = (140, 195, 255)          # exact (full-board) leaves

DISC_COLORS = {HUMAN: RUBY_RED, COMPUTER: AMBER_GOLD}

SS = 4                                # supersampling factor for ultra-crisp antialiasing


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


def make_background():
    """Build the vertical gradient with subtle atmospheric depth."""
    surf = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        pygame.draw.line(surf, color, (0, y), (WIDTH, y))

    # Subtle ambient top-center glow
    glow = pygame.Surface((WIDTH, 260), pygame.SRCALPHA)
    cx, cy = WIDTH // 2, 0
    for r in range(260, 0, -12):
        alpha = int(18 * (1.0 - r / 260))
        pygame.draw.ellipse(glow, (60, 90, 200, alpha),
                            (cx - r * 1.5, cy - r // 2, r * 3, r))
    surf.blit(glow, (0, 0))
    return surf


def make_disc(color):
    """
    Pre-render one 3D Polished Ceramic / Gem disc.
    Uses multi-layered offset radial highlights and a crisp specular glint.
    """
    size = RADIUS * 2 * SS
    big = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    r = RADIUS * SS

    # 1. Dark ambient drop rim / base shadow
    pygame.draw.circle(big, shade(color, 0.45), (c, c), r)

    # 2. Main spherical body with offset highlight center (top-left)
    layers = 16
    for i in range(layers):
        factor = 0.65 + 0.55 * (i / layers)
        layer_color = shade(color, factor)
        lr = int(r * (1.0 - 0.05 * i))
        # shift center slightly toward top-left (-x, -y)
        shift_x = int(c - (r * 0.18 * (i / layers)))
        shift_y = int(c - (r * 0.18 * (i / layers)))
        pygame.draw.circle(big, layer_color, (shift_x, shift_y), lr)

    # 3. Fine inner contour ring
    pygame.draw.circle(big, shade(color, 1.15), (int(c - r * 0.08), int(c - r * 0.08)),
                       int(r * 0.68), width=max(1, int(1.5 * SS)))

    # 4. Specular gloss glint (bright oval near top-left)
    glint_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    glint_w = int(r * 0.45)
    glint_h = int(r * 0.24)
    glint_rect = pygame.Rect(0, 0, glint_w, glint_h)
    glint_rect.center = (int(c - r * 0.35), int(c - r * 0.35))
    pygame.draw.ellipse(glint_surf, (255, 255, 255, 210), glint_rect)
    # rotate glint diagonally
    glint_surf = pygame.transform.rotate(glint_surf, 35)
    # blit glint back centered
    gw, gh = glint_surf.get_size()
    big.blit(glint_surf, (c - gw // 2 - int(r * 0.22), c - gh // 2 - int(r * 0.22)))

    # 5. Soft bottom ambient reflection rim
    rim_color = shade(color, 1.25) + (110,)
    rim_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(rim_surf, rim_color, (c, c), int(r * 0.94), width=max(1, int(2 * SS)))
    big.blit(rim_surf, (0, 0))

    return pygame.transform.smoothscale(big, (RADIUS * 2, RADIUS * 2))


def make_board_overlay():
    """
    Pre-render the sleek midnight board with countersunk 3D sockets.
    Features top inner shadows and bottom lip highlights for genuine depth.
    """
    w, h = BOARD_RECT.size
    big = pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)

    # Board body with rounded corners
    pygame.draw.rect(big, BOARD_BASE, (0, 0, w * SS, h * SS), border_radius=22 * SS)
    # Subtle top bevel highlight
    pygame.draw.rect(big, BOARD_LIP, (0, 0, w * SS, 6 * SS),
                     border_top_left_radius=22 * SS, border_top_right_radius=22 * SS)

    for r in range(ROWS):
        for c in range(COLS):
            cx = (c * SQUARE + SQUARE // 2) * SS
            cy = (r * SQUARE + SQUARE // 2) * SS

            # 1. Countersunk top inner shadow (creates socket depth)
            pygame.draw.circle(big, HOLE_SHADOW, (cx, cy - int(3 * SS)), (RADIUS + 4) * SS)

            # 2. Cut out the transparent hole
            pygame.draw.circle(big, (0, 0, 0, 0), (cx, cy), RADIUS * SS)

            # 3. Soft bottom-lip highlight
            lip_rect = pygame.Rect(cx - (RADIUS + 2) * SS, cy - (RADIUS + 2) * SS,
                                   (RADIUS + 2) * 2 * SS, (RADIUS + 2) * 2 * SS)
            pygame.draw.arc(big, HOLE_RIM, lip_rect, math.pi * 1.05, math.pi * 1.95,
                            max(1, int(2.5 * SS)))

    # Outer border ring
    pygame.draw.rect(big, BOARD_BORDER, (0, 0, w * SS, h * SS), width=int(2.5 * SS),
                     border_radius=22 * SS)

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


def draw_scoreboard(screen, board, font, small_font, human_turn, K):
    """
    Draw floating pill badges for Player and AI with active turn indicators.
    """
    human_fours, computer_fours = get_scores(board)
    mid_y = SCORE_H // 2 + 2

    # --- Left Pill: Human Player ---
    pill_w, pill_h = 160, 38
    pill_x = PAD_X
    pill_y = mid_y - pill_h // 2
    human_pill = pygame.Rect(pill_x, pill_y, pill_w, pill_h)

    # Background card
    pygame.draw.rect(screen, (22, 28, 56), human_pill, border_radius=19)
    border_color = RUBY_RED if human_turn else (45, 55, 95)
    border_w = 2 if human_turn else 1
    pygame.draw.rect(screen, border_color, human_pill, width=border_w, border_radius=19)

    # Player gem dot
    dot_x = pill_x + 19
    dot_y = mid_y
    pygame.draw.circle(screen, RUBY_RED, (dot_x, dot_y), 9)
    pygame.draw.circle(screen, (255, 255, 255), (dot_x - 3, dot_y - 3), 3)

    # Score text
    score_surf = font.render(f"YOU  {human_fours}", True, TEXT_WHITE)
    screen.blit(score_surf, (dot_x + 16, mid_y - score_surf.get_height() // 2))

    # --- Center Capsule: turn status, with K underneath ---
    center_w, center_h = 190, 30
    center_x = (WIDTH - center_w) // 2
    center_y = mid_y - 8 - center_h // 2
    center_rect = pygame.Rect(center_x, center_y, center_w, center_h)

    pygame.draw.rect(screen, (16, 20, 42), center_rect, border_radius=15)
    pygame.draw.rect(screen, (40, 50, 88), center_rect, width=1, border_radius=15)

    dots = ""
    if is_full(board):
        status_txt, status_col = "GAME OVER", TEXT_WHITE
    elif human_turn:
        status_txt, status_col = "YOUR TURN", RUBY_RED
    else:
        status_txt, status_col = "AI THINKING", AMBER_GOLD
        dots = "." * (1 + (pygame.time.get_ticks() // 350) % 3)

    status_surf = small_font.render(status_txt, True, status_col)
    status_rect = status_surf.get_rect(center=center_rect.center)
    screen.blit(status_surf, status_rect)
    if dots:                                # dots hang off the right edge: no jitter
        screen.blit(small_font.render(dots, True, status_col),
                    (status_rect.right + 1, status_rect.y))

    k_surf = small_font.render(f"search depth K = {K}", True, TEXT_MUTED)
    screen.blit(k_surf, k_surf.get_rect(center=(WIDTH // 2, mid_y + 17)))

    # --- Right Pill: Computer AI ---
    comp_x = WIDTH - PAD_X - pill_w
    comp_pill = pygame.Rect(comp_x, pill_y, pill_w, pill_h)

    pygame.draw.rect(screen, (22, 28, 56), comp_pill, border_radius=19)
    ai_border_color = AMBER_GOLD if not human_turn and not is_full(board) else (45, 55, 95)
    ai_border_w = 2 if not human_turn and not is_full(board) else 1
    pygame.draw.rect(screen, ai_border_color, comp_pill, width=ai_border_w, border_radius=19)

    # AI Score text
    ai_score_surf = font.render(f"{computer_fours}  AI", True, TEXT_WHITE)
    screen.blit(ai_score_surf, (comp_x + 22, mid_y - ai_score_surf.get_height() // 2))

    # AI gem dot
    ai_dot_x = comp_x + pill_w - 19
    ai_dot_y = mid_y
    pygame.draw.circle(screen, AMBER_GOLD, (ai_dot_x, ai_dot_y), 9)
    pygame.draw.circle(screen, (255, 255, 255), (ai_dot_x - 3, ai_dot_y - 3), 3)


def draw_game(screen, board, background, overlay, discs, hover_x=None, hover_player=HUMAN,
              falling=None, hovered_col=None, highlight=()):
    """Draw one complete frame of the game in layered order."""
    # 1. Background
    screen.blit(background, (0, 0))

    # 2. Spotlight beam down hovered column
    if hovered_col is not None and falling is None:
        draw_spotlight(screen, hovered_col)

    # 3. Smooth Hover Disc in the top strip
    if hover_x is not None and falling is None:
        t = pygame.time.get_ticks() * 0.004
        bob_y = HOVER_Y + math.sin(t) * 3.5
        screen.blit(discs[hover_player], (int(hover_x) - RADIUS, int(bob_y) - RADIUS))

        # Floating guide arrow pointing downward
        arrow_y = int(bob_y) + RADIUS + 4
        arrow = [
            (int(hover_x), arrow_y + 6),
            (int(hover_x) - 5, arrow_y),
            (int(hover_x) + 5, arrow_y)
        ]
        pygame.draw.polygon(screen, (200, 220, 255, 180), arrow)

    # 4. Hole interiors behind the board
    pygame.draw.rect(screen, HOLE_BACK, BOARD_RECT, border_radius=22)

    # 5. Settled discs inside the board
    for r in range(ROWS):
        for c in range(COLS):
            p = board[r][c]
            if p != EMPTY:
                x, y = cell_center(r, c)
                screen.blit(discs[p], (x - RADIUS, y - RADIUS))
                if (r, c) in highlight:     # disc is part of a connected-four
                    pygame.draw.circle(screen, (255, 255, 255), (x, y), RADIUS - 2, 3)

    # 6. Mid-drop disc with physics
    if falling is not None:
        fx, fy, player = falling
        screen.blit(discs[player], (int(fx) - RADIUS, int(fy) - RADIUS))

    # 7. Board chassis overlay in front
    screen.blit(overlay, BOARD_RECT.topleft)


def draw_game_over(screen, board, font, small_font):
    """
    Compact result banner in the strip above the board (the board itself stays
    fully visible, with every connected-four highlighted).
    """
    human, computer = get_scores(board)
    w = winner(board)

    if w == HUMAN:
        title, accent = "VICTORY! You outplayed the AI", RUBY_RED
    elif w == COMPUTER:
        title, accent = "AI WINS this round", AMBER_GOLD
    else:
        title, accent = "IT'S A DRAW", (110, 180, 255)

    card = pygame.Rect(PAD_X, SCORE_H + 6, WIDTH - 2 * PAD_X, HOVER_H - 12)
    pygame.draw.rect(screen, (20, 26, 54), card, border_radius=18)
    pygame.draw.rect(screen, accent, card, width=3, border_radius=18)

    title_surf = font.render(title, True, accent)
    screen.blit(title_surf, title_surf.get_rect(center=(card.centerx, card.top + 21)))
    info = f"YOU {human} - {computer} AI     [R] play again     [Esc] quit"
    info_surf = small_font.render(info, True, (210, 218, 245))
    screen.blit(info_surf, info_surf.get_rect(center=(card.centerx, card.bottom - 20)))


def draw_start_screen(screen, background, big_font, font, small_font, text, error):
    """
    Draw a clean, sleek start screen where the player enters search depth K.
    """
    screen.blit(background, (0, 0))
    cx = WIDTH // 2

    # Title & Subtitle
    title = big_font.render("CONNECT 4", True, TEXT_WHITE)
    screen.blit(title, title.get_rect(center=(cx, 160)))

    sub = small_font.render("MINIMAX AI WITH ALPHA-BETA PRUNING", True, (110, 140, 230))
    screen.blit(sub, sub.get_rect(center=(cx, 205)))

    # Card container for input
    card_w, card_h = 420, 260
    card = pygame.Rect(cx - card_w // 2, 260, card_w, card_h)
    pygame.draw.rect(screen, (22, 28, 58), card, border_radius=22)
    pygame.draw.rect(screen, (46, 62, 118), card, width=2, border_radius=22)

    # Prompt label
    prompt = font.render("Enter Search Depth (K)", True, TEXT_WHITE)
    screen.blit(prompt, prompt.get_rect(center=(cx, card.top + 45)))

    # Input Box with glowing focus border
    box = pygame.Rect(cx - 75, card.top + 85, 150, 62)
    pygame.draw.rect(screen, (12, 16, 36), box, border_radius=14)
    pygame.draw.rect(screen, AMBER_GOLD, box, width=2, border_radius=14)

    # Blinking smooth cursor
    cursor = "|" if (pygame.time.get_ticks() // 450) % 2 == 0 else " "
    typed = big_font.render(text + cursor, True, TEXT_WHITE)
    screen.blit(typed, typed.get_rect(center=box.center))

    # Helper guidance
    hint = small_font.render("Type a number (1 to 7 recommended) and press Enter", True, TEXT_MUTED)
    screen.blit(hint, hint.get_rect(center=(cx, card.top + 175)))

    if error:
        err_surf = small_font.render(error, True, RUBY_RED)
        screen.blit(err_surf, err_surf.get_rect(center=(cx, card.top + 215)))
    else:
        esc_hint = small_font.render("Press Esc to Quit", True, (90, 105, 145))
        screen.blit(esc_hint, esc_hint.get_rect(center=(cx, card.top + 215)))


def ask_k_screen(screen, background, big_font, font, small_font):
    """Prompt the user to type depth K. Returns int K or None on quit."""
    text, error = "", ""
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                    error = ""
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if text and text.isdigit() and int(text) >= 1:
                        return int(text)
                    error = "Please enter a valid depth (1 or higher)"
                elif event.unicode.isascii() and event.unicode.isdigit() and len(text) < 2:
                    text += event.unicode
                    error = ""

        draw_start_screen(screen, background, big_font, font, small_font, text, error)
        pygame.display.flip()
        clock.tick(60)


def format_time(seconds):
    """Milliseconds below one second, otherwise seconds."""
    return f"{seconds * 1000:.0f} ms" if seconds < 1 else f"{seconds:.2f} s"


def draw_stats(screen, history, thinking, tree_open, fonts):
    """
    Stats strip under the board: details of the computer's last move
    (column, minimax value, nodes expanded, time, cut branches), running
    totals, and the button that shows/hides the tree panel.
    """
    rect = STATS_RECT
    pygame.draw.rect(screen, (20, 26, 54), rect, border_radius=16)
    pygame.draw.rect(screen, (46, 62, 118), rect, width=1, border_radius=16)

    last = history[-1] if history else None
    if thinking:
        cells = [("AI MOVE", "thinking", AMBER_GOLD)] + [(n, "...", TEXT_MUTED) for n in
                                                          ("VALUE", "NODES", "TIME", "CUT")]
    elif last:
        cells = [("AI MOVE", f"#{last['move']}  col {last['col']}", AMBER_GOLD),
                 ("VALUE", f"{last['value']}", TEXT_WHITE),
                 ("NODES", f"{last['nodes']:,}", TEXT_WHITE),
                 ("TIME", format_time(last["time"]), TEXT_WHITE),
                 ("CUT", "-" if last["pruned"] is None else f"{last['pruned']:,}", TEXT_WHITE)]
    else:
        cells = [(n, "-", TEXT_MUTED) for n in ("AI MOVE", "VALUE", "NODES", "TIME", "CUT")]

    col_w = 88
    for i, (label, value, color) in enumerate(cells):
        x = rect.x + 16 + i * col_w
        screen.blit(fonts["tiny"].render(label, True, TEXT_MUTED), (x, rect.y + 10))
        screen.blit(fonts["small"].render(value, True, color), (x, rect.y + 26))

    if history:
        total_nodes = sum(h["nodes"] for h in history)
        total_time = sum(h["time"] for h in history)
        footer = (f"Totals over {len(history)} AI moves: {total_nodes:,} nodes, "
                  f"{format_time(total_time)}, avg {total_nodes // len(history):,} nodes/move")
    else:
        footer = "Stats appear after the computer's first move."
    screen.blit(fonts["tiny"].render(footer, True, TEXT_MUTED), (rect.x + 16, rect.bottom - 24))

    # Tree toggle button
    pygame.draw.rect(screen, (30, 40, 80) if tree_open else (16, 20, 42), TREE_BUTTON,
                     border_radius=10)
    pygame.draw.rect(screen, AMBER_GOLD if tree_open else (60, 76, 130), TREE_BUTTON,
                     width=2, border_radius=10)
    label = fonts["small"].render("TREE [T]", True, TEXT_WHITE)
    screen.blit(label, label.get_rect(center=TREE_BUTTON.center))


class TreePanel:
    """
    Scrollable, collapsible view of the minimax tree of the last AI move.
    Gold rows = the chosen path, grey struck-through rows = pruned branches.
    Click a row to open/close it; mouse wheel scrolls.
    """

    ROW_H = 22
    HEADER_H = 108
    BUTTONS = ("Expand all", "Collapse all", "Chosen path")

    def __init__(self):
        self.root = None
        self.info = None
        self.expanded = set()
        self.path = set()
        self.rows = []
        self.scroll = 0

    # ----- state -----
    def clear(self):
        """Forget the tree (new game)."""
        self.root, self.info, self.rows = None, None, []
        self.expanded, self.path, self.scroll = set(), set(), 0

    def set_tree(self, root, info):
        """Show a new tree; start with the chosen path open."""
        self.root, self.info = root, info
        self.path = set(principal_path(root))
        self.expanded = default_expanded(root)
        self.scroll = 0
        self._refresh()

    def _refresh(self):
        self.rows = visible_rows(self.root, self.expanded) if self.root else []
        self.scroll = max(0, min(self.scroll, self._max_scroll()))

    def _list_rect(self, rect):
        return pygame.Rect(rect.x + 12, rect.y + self.HEADER_H,
                           rect.width - 24, rect.height - self.HEADER_H - 14)

    def _max_scroll(self):
        return max(0, len(self.rows) * self.ROW_H - self._list_rect(PANEL_RECT).height)

    def _button_rects(self, rect):
        w, gap = 112, 8
        return [pygame.Rect(rect.x + 12 + i * (w + gap), rect.y + 66, w, 28)
                for i in range(len(self.BUTTONS))]

    def scroll_by(self, pixels):
        """Scroll the list (positive = down), staying inside the list."""
        self.scroll = max(0, min(self.scroll + pixels, self._max_scroll()))

    # ----- input -----
    def click(self, pos, rect):
        """Handle a left click inside the panel (buttons or a tree row)."""
        if self.root is None:
            return
        for i, button in enumerate(self._button_rects(rect)):
            if button.collidepoint(pos):
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
                if has_children:
                    (self.expanded.discard if is_open else self.expanded.add)(node)
                    self._refresh()

    # ----- drawing -----
    def draw(self, screen, rect, fonts):
        """Draw the whole panel."""
        pygame.draw.rect(screen, (13, 16, 33), rect)
        pygame.draw.line(screen, (46, 62, 118), rect.topleft, rect.bottomleft, 2)
        screen.blit(fonts["font"].render("MINIMAX TREE", True, TEXT_WHITE), (rect.x + 14, rect.y + 10))

        if self.root is None:
            msg = fonts["small"].render("The tree appears after the computer's first move.",
                                        True, TEXT_MUTED)
            screen.blit(msg, (rect.x + 14, rect.y + 60))
            return

        i = self.info
        sub = (f"AI move #{i['move']}  |  K = {i['K']}  |  chose column {i['col']}  |  "
               f"{i['nodes']:,} nodes, {i['pruned']:,} cut")
        screen.blit(fonts["tiny"].render(sub, True, TEXT_MUTED), (rect.x + 14, rect.y + 40))
        legend = fonts["tiny"].render("gold = chosen path     grey = pruned     "
                                      "click a row to open / close", True, (110, 125, 165))
        screen.blit(legend, (rect.x + 14, rect.y + 54))

        for label, button in zip(self.BUTTONS, self._button_rects(rect)):
            pygame.draw.rect(screen, (22, 28, 58), button, border_radius=8)
            pygame.draw.rect(screen, (60, 76, 130), button, width=1, border_radius=8)
            text = fonts["tiny"].render(label, True, TEXT_WHITE)
            screen.blit(text, text.get_rect(center=button.center))

        area = self._list_rect(rect)
        old_clip = screen.get_clip()
        screen.set_clip(area)
        first = self.scroll // self.ROW_H
        count = area.height // self.ROW_H + 2
        for n in range(first, min(first + count, len(self.rows))):
            self._draw_row(screen, area, n, fonts)
        screen.set_clip(old_clip)

        if self._max_scroll() > 0:               # scrollbar thumb
            track = pygame.Rect(area.right - 6, area.y, 5, area.height)
            thumb_h = max(24, area.height * area.height // (len(self.rows) * self.ROW_H))
            thumb_y = area.y + (area.height - thumb_h) * self.scroll // self._max_scroll()
            pygame.draw.rect(screen, (28, 36, 70), track, border_radius=3)
            pygame.draw.rect(screen, (90, 110, 175), (track.x, thumb_y, 5, thumb_h), border_radius=3)

    def _draw_row(self, screen, area, n, fonts):
        """Draw row n: triangle, label, alpha, beta and value."""
        node, has_children, is_open = self.rows[n]
        y = area.y + n * self.ROW_H - self.scroll
        row_rect = pygame.Rect(area.x, y, area.width - 10, self.ROW_H - 2)
        on_path = node in self.path

        if on_path:
            pygame.draw.rect(screen, (52, 46, 22), row_rect, border_radius=5)
            pygame.draw.rect(screen, AMBER_GOLD, (row_rect.x, row_rect.y, 3, row_rect.height))

        x = area.x + 10 + node.depth * 14
        mid = y + self.ROW_H // 2 - 1
        if has_children:
            if is_open:
                points = [(x, mid - 3), (x + 8, mid - 3), (x + 4, mid + 3)]
            else:
                points = [(x + 1, mid - 5), (x + 1, mid + 5), (x + 7, mid)]
            pygame.draw.polygon(screen, PRUNED_GREY if node.pruned else TEXT_MUTED, points)
        x += 14

        if node.pruned:
            label_color = detail_color = PRUNED_GREY
        else:
            if node.is_leaf:
                label_color = FINAL_BLUE if node.final else LEAF_GREEN
            else:
                label_color = AMBER_GOLD if node.kind == "MAX" else (255, 120, 140)
            detail_color = TEXT_WHITE if on_path else (190, 198, 225)

        label = fonts["row"].render(node_label(node), True, label_color)
        screen.blit(label, (x, y + 2))
        if node.pruned:                          # strike through the label
            pygame.draw.line(screen, PRUNED_GREY, (x, mid), (x + label.get_width(), mid), 1)
        details = (f"\u03b1={fmt_bound(node.alpha)}  \u03b2={fmt_bound(node.beta)}   "
                   f"{node_tail(node)}")
        screen.blit(fonts["row"].render(details, True, detail_color), (x + label.get_width() + 14, y + 2))


def animate_drop(render, col, row, player, current_hover_x=None):
    """
    Drop a disc with realistic gravity and an elastic landing bounce.
    Rebounds smoothly upon hitting the landing row before settling.
    """
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
                speed = -speed * 0.32        # elastic rebound
                bounces += 1
            else:
                break

        render(falling=(x, y, player), hover_x=current_hover_x)
        pygame.event.pump()
        clock.tick(60)


def start_ai_job(board, K):
    """
    Run choose_move in a background thread so the window stays responsive
    while the AI thinks. Returns a dict with the thread and, once it has
    finished, "result" = (col, stats) or "error" = the exception.
    """
    snapshot = [row[:] for row in board]
    job = {"result": None, "error": None}

    def work():
        try:
            job["result"] = choose_move(snapshot, K)    # also prints + saves the tree
        except Exception as exc:                        # re-raised in the GUI thread
            job["error"] = exc

    job["thread"] = threading.Thread(target=work, daemon=True)
    job["thread"].start()
    return job


class GameState:
    """Everything that changes during one game (reset for 'play again')."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.board = new_board()
        self.human_turn = True
        self.computer_move_at = 0       # tick at which the AI may start thinking
        self.history = []               # one stats dict per AI move
        self.fours = set()              # cells to highlight
        self.ai_job = None


def main():
    """Start screen for K, then the game loop."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Connect 4 - Minimax AI")

    face = "segoeui,arial,helvetica"
    fonts = {
        "font": pygame.font.SysFont(face, 24, bold=True),
        "small": pygame.font.SysFont(face, 16, bold=True),
        "tiny": pygame.font.SysFont(face, 12, bold=True),
        "row": pygame.font.SysFont(face, 14),
        "big": pygame.font.SysFont(face, 48, bold=True),
    }

    # Pre-render visual assets once
    background = make_background()
    overlay = make_board_overlay()
    discs = {p: make_disc(col) for p, col in DISC_COLORS.items()}

    K = ask_k_screen(screen, background, fonts["big"], fonts["font"], fonts["small"])
    if K is None:
        pygame.quit()
        return

    state = GameState()
    panel = TreePanel()
    show_tree = False
    smooth_hover_x = WIDTH // 2
    clock = pygame.time.Clock()

    def toggle_tree():
        """Show/hide the tree panel; the window grows to the right to fit it."""
        nonlocal screen, show_tree
        show_tree = not show_tree
        screen = pygame.display.set_mode((WIDTH + (PANEL_W if show_tree else 0), HEIGHT))

    def render(hover_x=None, falling=None, active_col=None):
        """Draw and display one complete frame."""
        draw_game(screen, state.board, background, overlay, discs,
                  hover_x=hover_x,
                  hover_player=HUMAN if state.human_turn else COMPUTER,
                  falling=falling, hovered_col=active_col, highlight=state.fours)
        draw_scoreboard(screen, state.board, fonts["font"], fonts["small"], state.human_turn, K)
        draw_stats(screen, state.history, not state.human_turn and not is_full(state.board),
                   show_tree, fonts)
        if show_tree:
            panel.draw(screen, PANEL_RECT, fonts)
        if is_full(state.board):
            draw_game_over(screen, state.board, fonts["font"], fonts["small"])
        pygame.display.flip()

    def finish_ai_move():
        """The AI thread is done: animate its disc, record stats, feed the tree panel."""
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
        if stats["root"] is not None:
            panel.set_tree(stats["root"], entry)
        print(f"Computer plays column {col + 1} "
              f"(value={stats['value']}, nodes={stats['nodes']}, "
              f"cut={stats['pruned']}, time={stats['time']:.4f}s)")
        # Clicks made while the AI was thinking/animating must not become moves.
        pygame.event.clear(pygame.MOUSEBUTTONDOWN)

    running = True
    while running:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        # Only the board area counts as a column (not the stats strip below it).
        mouse_col = column_at(mouse_x) if mouse_y < BOARD_RECT.bottom else None

        # Smooth glide towards mouse column
        if mouse_col is not None and mouse_col in get_valid_moves(state.board):
            target_x = cell_center(0, mouse_col)[0]
            smooth_hover_x += (target_x - smooth_hover_x) * 0.28
            active_hover_col = mouse_col
        else:
            active_hover_col = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_t:
                    toggle_tree()
                elif event.key == pygame.K_r and is_full(state.board):
                    state.reset()
                    panel.clear()
            elif event.type == pygame.MOUSEWHEEL:
                if show_tree and PANEL_RECT.collidepoint(pygame.mouse.get_pos()):
                    panel.scroll_by(-event.y * TreePanel.ROW_H * 3)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if TREE_BUTTON.collidepoint(event.pos):
                    toggle_tree()
                elif show_tree and PANEL_RECT.collidepoint(event.pos):
                    panel.click(event.pos, PANEL_RECT)
                elif event.pos[1] < BOARD_RECT.bottom:
                    col = column_at(event.pos[0])
                    if state.human_turn and col is not None and col in get_valid_moves(state.board):
                        after, row = drop_piece(state.board, col, HUMAN)
                        animate_drop(render, col, row, HUMAN, current_hover_x=smooth_hover_x)
                        state.board = after
                        state.fours = four_cells(after)
                        state.human_turn = False
                        state.computer_move_at = pygame.time.get_ticks() + 200

        show_hover = smooth_hover_x if state.human_turn and active_hover_col is not None else None
        render(hover_x=show_hover, active_col=active_hover_col)

        # Computer's turn: think in a background thread, then play the move.
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
