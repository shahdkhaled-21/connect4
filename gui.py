"""
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
import pygame

from main import choose_move
from engine import (ROWS, COLS, EMPTY, HUMAN, COMPUTER, new_board,
                    get_valid_moves, drop_piece, get_scores, is_full, winner)

# ---------- Layout & Geometry ----------
SQUARE = 100                          # pixel size of one cell
PAD_X = 24                            # horizontal margin around the board
PAD_BOTTOM = 24                       # bottom margin
SCORE_H = 68                          # height of the top scoreboard bar
HOVER_H = SQUARE                      # height of hover guide zone
TOP = SCORE_H + HOVER_H               # top coordinate of the board
HOVER_Y = SCORE_H + HOVER_H // 2      # resting vertical center for hover disc
RADIUS = SQUARE // 2 - 9              # radius of a hole / disc
WIDTH = COLS * SQUARE + 2 * PAD_X
HEIGHT = TOP + ROWS * SQUARE + PAD_BOTTOM
BOARD_RECT = pygame.Rect(PAD_X, TOP, COLS * SQUARE, ROWS * SQUARE)

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

    # --- Center Capsule: Turn / Depth Status ---
    center_w, center_h = 140, 30
    center_x = (WIDTH - center_w) // 2
    center_y = mid_y - center_h // 2
    center_rect = pygame.Rect(center_x, center_y, center_w, center_h)

    pygame.draw.rect(screen, (16, 20, 42), center_rect, border_radius=15)
    pygame.draw.rect(screen, (40, 50, 88), center_rect, width=1, border_radius=15)

    if is_full(board):
        status_txt = "GAME OVER"
        status_col = TEXT_WHITE
    elif human_turn:
        status_txt = "YOUR TURN"
        status_col = RUBY_RED
    else:
        status_txt = "AI THINKING..."
        status_col = AMBER_GOLD

    status_surf = small_font.render(status_txt, True, status_col)
    screen.blit(status_surf, status_surf.get_rect(center=center_rect.center))

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
              falling=None, hovered_col=None):
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

    # 6. Mid-drop disc with physics
    if falling is not None:
        fx, fy, player = falling
        screen.blit(discs[player], (int(fx) - RADIUS, int(fy) - RADIUS))

    # 7. Board chassis overlay in front
    screen.blit(overlay, BOARD_RECT.topleft)


def draw_game_over(screen, board, big_font, font, small_font):
    """Display a sleek frosted glass modal dialog with game results and rematch hints."""
    human, computer = get_scores(board)
    w = winner(board)

    if w == HUMAN:
        title, accent = "VICTORY!", RUBY_RED
        subtitle = "Congratulations! You outplayed the AI."
    elif w == COMPUTER:
        title, accent = "AI WINS!", AMBER_GOLD
        subtitle = "Good game! The computer took this round."
    else:
        title, accent = "IT'S A DRAW!", (110, 180, 255)
        subtitle = "An equally matched battle."

    # Semi-transparent dark blur backdrop
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((5, 8, 18, 195))
    screen.blit(dim, (0, 0))

    # Modal Card
    card_w, card_h = 520, 290
    card = pygame.Rect((WIDTH - card_w) // 2, (HEIGHT - card_h) // 2, card_w, card_h)

    # Card background & glowing border
    pygame.draw.rect(screen, (20, 26, 54), card, border_radius=24)
    pygame.draw.rect(screen, accent, card, width=3, border_radius=24)

    # Header title
    title_surf = big_font.render(title, True, accent)
    screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, card.top + 55)))

    # Subtitle
    sub_surf = small_font.render(subtitle, True, TEXT_MUTED)
    screen.blit(sub_surf, sub_surf.get_rect(center=(WIDTH // 2, card.top + 98)))

    # Score display box
    score_box = pygame.Rect(card.centerx - 180, card.top + 130, 360, 60)
    pygame.draw.rect(screen, (14, 18, 38), score_box, border_radius=16)
    pygame.draw.rect(screen, (38, 48, 88), score_box, width=1, border_radius=16)

    score_str = f"YOU : {human}    —    {computer} : AI"
    score_surf = font.render(score_str, True, TEXT_WHITE)
    screen.blit(score_surf, score_surf.get_rect(center=score_box.center))

    # Footer key hints
    hint_surf = small_font.render("Press  [ R ]  to Play Again   •   [ Esc ]  to Quit",
                                  True, (210, 218, 245))
    screen.blit(hint_surf, hint_surf.get_rect(center=(WIDTH // 2, card.bottom - 40)))


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
    hint = small_font.render("Type a number (e.g. 1 to 8) and press Enter", True, TEXT_MUTED)
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
                elif event.unicode.isdigit() and len(text) < 2:
                    text += event.unicode
                    error = ""

        draw_start_screen(screen, background, big_font, font, small_font, text, error)
        pygame.display.flip()
        clock.tick(60)


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


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Connect 4")

    font = pygame.font.SysFont("segoeui,arial,helvetica", 24, bold=True)
    small_font = pygame.font.SysFont("segoeui,arial,helvetica", 16, bold=True)
    big_font = pygame.font.SysFont("segoeui,arial,helvetica", 48, bold=True)

    # Pre-render visual assets once
    background = make_background()
    overlay = make_board_overlay()
    discs = {p: make_disc(col) for p, col in DISC_COLORS.items()}

    # Ask search depth K (player types it)
    K = ask_k_screen(screen, background, big_font, font, small_font)
    if K is None:
        pygame.quit()
        return

    board = new_board()
    human_turn = True
    computer_move_at = 0
    clock = pygame.time.Clock()

    # Smooth hover tracking state
    smooth_hover_x = WIDTH // 2

    def render(hover_x=None, falling=None, active_col=None):
        """Draw and display one complete frame."""
        draw_game(screen, board, background, overlay, discs,
                  hover_x=hover_x,
                  hover_player=HUMAN if human_turn else COMPUTER,
                  falling=falling,
                  hovered_col=active_col)
        draw_scoreboard(screen, board, font, small_font, human_turn, K)
        if is_full(board):
            draw_game_over(screen, board, big_font, font, small_font)
        pygame.display.flip()

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_col = column_at(mouse_pos[0])

        # Smooth glide towards mouse column
        if mouse_col is not None and mouse_col in get_valid_moves(board):
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
                elif event.key == pygame.K_r and is_full(board):
                    board = new_board()
                    human_turn = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                col = column_at(event.pos[0])
                if human_turn and col is not None and col in get_valid_moves(board):
                    after, row = drop_piece(board, col, HUMAN)
                    # Smooth animated drop with elastic bounce
                    animate_drop(render, col, row, HUMAN, current_hover_x=smooth_hover_x)
                    board = after
                    human_turn = False
                    computer_move_at = pygame.time.get_ticks() + 200

        # Draw frame
        show_hover = smooth_hover_x if human_turn and active_hover_col is not None else None
        render(hover_x=show_hover, active_col=active_hover_col)

        # Computer's turn
        if not human_turn and get_valid_moves(board) and pygame.time.get_ticks() >= computer_move_at:
            col, stats = choose_move(board, K)
            after, row = drop_piece(board, col, COMPUTER)
            target_ai_x = cell_center(0, col)[0]
            animate_drop(render, col, row, COMPUTER, current_hover_x=target_ai_x)
            board = after
            print(f"Computer plays column {col + 1} "
                  f"(value={stats['value']}, nodes={stats['nodes']}, "
                  f"time={stats['time']:.4f}s)")
            human_turn = True

        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()