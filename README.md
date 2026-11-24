# Connect 4 AI Agent

Human vs. computer Connect 4 on a 7x6 board. The computer uses **minimax with
alpha-beta pruning**, truncated at depth **K** (entered before the game) and
scored by a heuristic function. The game does not stop at the first four: play
continues until the board is full, and the winner is the player with more
connected-fours (overlapping fours count separately).

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
| `python main.py` | Console game. Asks for K, then you play (you move first) |
| `python gui.py` | Pygame GUI with a start screen for K |
| `python experiments.py` | Time and nodes expanded for K = 1..7 (without pruning up to K = 6), CSVs and charts in `results/` (about 3 minutes) |
| `python compare.py 2 3 4` | Heuristic tournament (`h1` to `h4`): every pair, both sides, 15 random openings, for each K given. Writes `results/comparison.csv` (about 3 minutes) |
| `python -m pytest -v` | All tests |

On every computer turn the minimax tree is printed to the console and saved
to `trees/turn_<n>.txt`. Each line shows the node type, the column played
(1 to 7), alpha, beta, and the value; leaves show the heuristic value `h=`
and cut branches are marked `PRUNED`.

## Project layout

| File | Contents |
|---|---|
| `engine.py` | Board, moves, counting connected-fours, scores, winner |
| `ai.py` | Minimax + alpha-beta, `choose_move` |
| `heuristic.py` | Heuristics `h1` to `h4` (four-difference, windows, playable threats, center control, parity). `h4` is the default |
| `tree.py` | Tree node, console printer, file and JSON export |
| `main.py` | Console game loop |
| `gui.py` | Pygame GUI |
| `experiments.py` | Time/nodes vs. K experiments and charts |
| `compare.py` | AI vs. AI heuristic comparison |
| `tests/` | Unit tests for the engine, heuristics and AI |
| `results/`, `trees/` | Generated output |
| `report/` | The report |

## Conventions

- Board: `board[row][col]`, row 0 is the top, 6 rows x 7 columns.
- Cells: `0` empty, `1` human, `2` computer.
- Columns are 0-based in code and shown as 1 to 7 to the user.
- Heuristics have the signature `h(board, me) -> int` (bigger is better for `me`).
- `choose_move(board, K, use_pruning=True, print_tree=True, heuristic=None, player=COMPUTER)`
  returns `(column, stats)` with `stats = {"nodes", "time", "value"}`.