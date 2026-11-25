# Connect 4 AI Agent

Human vs. computer Connect 4 on a 6x7 board. The computer picks its move with
**minimax with alpha-beta pruning**, cut off after **K levels** (K is entered
before the game) and evaluated with a heuristic function. In every computer
turn the minimax tree is printed to the console and saved to a file. A Pygame
GUI with a toggleable tree panel is included.

Alexandria University, Faculty of Engineering, Computer and Systems Department.
Artificial Intelligence course, Assignment 2.

Team: jana khaled (24010165), shahd khaled (24010333)

The full write-up (assumptions, heuristic details, sample trees, time and node
analysis) is in the report in `report/`. This file is the quick guide.

## Requirements

- Python 3.10 or newer (developed on 3.14)
- Packages: `pytest`, `pygame-ce`, `matplotlib`

```
python -m venv venv
venv\Scripts\activate          # Windows (PowerShell / cmd)
source venv/bin/activate       # macOS / Linux / Git Bash: source venv/Scripts/activate
pip install -r requirements.txt
```

Note: the GUI uses `pygame-ce`, not `pygame`, because `pygame` has no wheel
for recent Python versions.

## Run

| Command | What it does |
|---|---|
| `python main.py` | Console game. Asks for K, then you play (you move first). Prints the tree with leaf boards by default |
| `python main.py --tree-depth N` | Same, but prints only the first N levels of the tree in the console (recommended for K >= 5 to shorten console output; the saved file keeps the full tree) |
| `python main.py --no-boards` | Same, but hides the board under every leaf of the tree |
| `python gui.py` | Pygame GUI with a start screen for K |
| `python experiments.py` | Time and nodes vs. K = 1..6 (without pruning up to K = 5). Writes CSVs and charts to `results/` (a few minutes) |
| `python compare.py 2 3 4` | Heuristic tournament `h1` to `h4`, one run per K given. Writes `results/comparison.csv` and `results/comparison_summary.csv` (a few minutes; it saves after each K) |
| `python -m pytest -v` | All tests |

**GUI keys:** `T` (or the TREE button) shows/hides the tree panel, `R` plays
again after a game, `Esc` quits. Under the board a stats strip shows the
computer's last move: column, minimax value, nodes expanded, time and cut
branches, plus running totals. In the tree panel click a row to open/close it,
use the mouse wheel to scroll; the chosen path is gold and pruned nodes are
grey and struck through. Every node shows alpha, beta and its value.

## Rules and assumptions

- 6 rows x 7 columns. The human always moves first (red), the computer second
  (yellow). Colours are fixed.
- Play continues until the board is full (42 discs). The winner is the player
  with more connected-fours; equal counts is a draw.
- Every group of four consecutive equal discs counts as one four, so five in a
  row is 2 fours and a disc can belong to several fours.
- Columns are numbered 1 to 7 for the user. K is an integer >= 1 (K up to 6 or
  7 is practical).
- The AI is deterministic. Equal-valued moves are resolved by the move order
  (centre column first).

## How it works

**Search.** The computer is MAX, the human MIN. Children are tried in
centre-first order (4, 3, 5, 2, 6, 1, 7) so cut-offs happen early. The search
stops at depth K or at a full board. A cut-off happens when alpha >= beta; the
skipped children appear in the tree as `PRUNED` but are never searched or
counted. Alpha-beta was checked against plain minimax on 240 random positions:
same value and same move every time.

**Leaves.** At depth K the value is the heuristic (`h=` in the tree). On a full
board it is exact, 1000 x (computer fours - human fours), shown as `[FINAL]`
and `score=`.

**Tree output.** One node per line, indented by depth:

```
[MAX] root                       a=-18 b=+inf   value=-18
  [MIN] col=3 (comp)             a=-18 b=-27    value=-27
    [LEAF] col=4 (human)         a=-18 b=+inf   h=-27
    [MAX] col=3 (human)          a=-18 b=-27    PRUNED
```

`kind` (MAX/MIN) is who moves next from that node, `col` is the column played
to reach it, `a` and `b` are alpha and beta.

**Heuristics.** All score the board from the computer's point of view (bigger =
computer nearer to winning, negative = human nearer). Each adds one idea to the
previous one:

| Heuristic | Definition |
|---|---|
| `h1` | 100 x (computer fours - human fours) + window score |
| `h2` | `h1` + playable-threat bonus |
| `h3` | `h2` + centre bonus |
| `h4` (default) | `h2` + 3 x centre bonus + parity bonus |

- **Window score:** each of the 69 windows of four cells that holds only one
  side's discs counts 1, 5 or 20 for 1, 2 or 3 discs (negative for the human);
  windows with both colours are dead.
- **Playable threat:** +15 / -15 for a window with 3 discs and one empty cell
  that can be played right now.
- **Centre:** per-disc weight by column 0, 1, 2, 3, 2, 1, 0.
- **Parity:** +10 / -10 for a 3-disc window whose empty cell is not yet
  playable but sits at a height its owner naturally gets (human odd, computer
  even).

## Key results

Average nodes expanded per move (one game per setting, from
`results/experiments_summary.csv`):

| K | With pruning | Without pruning |
|---|---|---|
| 2 | 21.5 | 37.3 |
| 3 | 106.6 | 253.9 |
| 4 | 349.6 | 1,376 |
| 5 | 1,390 | 9,009 |
| 6 | 4,499 | not run |

Heuristic tournament, wins / ties / losses of each heuristic out of 90 games
per K (from `results/comparison_summary.csv`):

| K | h1 | h2 | h3 | h4 |
|---|---|---|---|---|
| 2 | 31 / 33 / 26 | 17 / 38 / 35 | 28 / 32 / 30 | **35 / 35 / 20** |
| 3 | 32 / 29 / 29 | 19 / 24 / 47 | 28 / 28 / 34 | **47 / 27 / 16** |
| 4 | 21 / 42 / 27 | 18 / 33 / 39 | 26 / 35 / 29 | **38 / 44 / 8** |

## Project layout

| File | Contents |
|---|---|
| `engine.py` | Board, moves, counting connected-fours, scores, winner |
| `ai.py` | Minimax + alpha-beta, move ordering, `choose_move` |
| `heuristic.py` | Heuristics `h1` to `h4` |
| `tree.py` | Tree node, console printer, file and JSON export |
| `main.py` | Console game loop |
| `gui.py` | Pygame GUI (board, stats strip, tree panel) |
| `tree_view.py` | Logic of the GUI tree panel (chosen path, visible rows), no pygame |
| `experiments.py` | Time/nodes vs. K experiments and charts |
| `compare.py` | AI vs. AI heuristic comparison |
| `tests/` | Unit tests for the engine, heuristics, AI, tree tools and input handling |
| `results/` | CSVs, charts and `sample_trees/` (three example trees) |
| `trees/` | Per-turn tree files written while playing (not tracked by git) |
| `report/` | The report |

## Conventions

- Board: `board[row][col]`, row 0 is the top, 6 rows x 7 columns.
- Cells: `0` empty, `1` human, `2` computer.
- Columns are 0-based in code and shown as 1 to 7 to the user.
- Heuristics have the signature `h(board, me) -> int` (bigger is better for `me`).
- `choose_move(board, K, use_pruning=True, print_tree=True, heuristic=None,
  player=COMPUTER, tree_depth=None, show_boards=True)` returns
  `(column, stats)` with `stats = {"nodes", "time", "value", "pruned", "root"}`.
  `pruned` and `root` are `None` when `print_tree=False`, because no tree is
  built in that case.
