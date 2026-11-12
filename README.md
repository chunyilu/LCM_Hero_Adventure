# ⚔️ LCM Hero Adventure

[![Run Game Tests](https://github.com/chunyilu/LCM_Hero_Adventure/actions/workflows/test.yml/badge.svg)](https://github.com/chunyilu/LCM_Hero_Adventure/actions/workflows/test.yml)

**LCM Hero Adventure** is a 2D educational math JRPG built with Python and `pygame-ce` that teaches **Least Common Multiples (LCM)** through turn-based Mathematical Shield battles, interactive Short Division (短除法) tutorials, and an offline Adaptive Edge AI difficulty model.

---

## ✨ Key Features

- **🛡️ Mathematical Shield Combat**: Monsters carry shields displaying 2 or 3 numbers (e.g., `[4, 6]`). Cast the correct Least Common Multiple spell card to shatter the shield and defeat the monster; choosing a non-least common multiple (e.g., `24` for `[4, 6]`) triggers targeted educational feedback.
- **🗺️ 4 Pedagogical Level Zones**:
  1. **Whispering Woods** — *Prime Pairs* (e.g., `[3, 5]`, coprime numbers where $\text{LCM} = a \times b$).
  2. **Shadow Caves** — *Overlapping Factors* (e.g., `[4, 6]`, shared prime factors).
  3. **Misty Barrens** — *Contained Multiples* (e.g., `[3, 6]`, where the larger number is a multiple of the smaller).
  4. **Demon Castle** — *Three-Number Rush* (e.g., `[3, 4, 6]`, compounding LCM across three numbers).
- **🧚 "Short Division" (短除法) Tutorial Fairy**: Automatically triggers after 2 consecutive mistakes (or on-demand via `H`), walking through step-by-step Short Division and side-by-side Multiples Listing.
- **🤖 Adaptive Edge AI (Offline Performance Model)**: Tracks per-problem-type response latency and accuracy. Taking $>15\text{s}$ or making mistakes dynamically boosts reinforcement spawn weights for that mathematical pattern until mastery improves.
- **🏪 Village Equipment Shop & Princess Rescue Progression**: Earn Star Points and Gold Coins to purchase **The Multiplier Sword** and **The Prime Number Shield**, and unlock stage-end Princess cutscenes across all 4 zones.

---

## 🏗️ Architecture (MVC)

```text
[Arithmetic State Engine (mvc/model.py)] <--> [Main Pygame Loop (mvc/controller.py)] <--> [Render Layer / UI (mvc/view.py)]
```

- `mvc/model.py` — Pure Python arithmetic engine, Short Division solver, Adaptive Edge AI, shop, and progression state.
- `mvc/view.py` — Procedural pixel/vector rendering, particle effects, UI hit-boxes, and synthesized retro chiptune audio.
- `mvc/controller.py` — Event loop, keyboard/mouse handling, and combat response timer.
- `tests/test_game.py` — Automated pytest suite covering arithmetic logic, AI adaptation, progression, and headless rendering.

---

## 🚀 Getting Started

### 1. Local Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Game

```bash
./run_game.sh
# or directly:
python main.py
```

---

## 🎮 Controls

| Context | Input | Action |
| :--- | :--- | :--- |
| **Title / Cutscenes** | `Enter` / `Space` / Click | Start game / Advance cutscene |
| **Exploration Map** | `Arrow Keys` / `WASD` | Move Hero across tiles |
| **Exploration Overlays** | `B` / `I` / `L` | Open **Shop** (`B`), **AI Telemetry** (`I`), **Leaderboard** (`L`) |
| **Combat** | `1`–`4` or Mouse Click | Cast Spell Card `1`–`4` |
| **Combat** | `H` | Summon the **Short Division Tutorial Fairy** |
| **Tutorial Fairy** | `T` / `Right` / `Left` | Toggle Short Division vs. Multiples View / Step through |

---

## 🧪 Running Tests & Docker

### Run Locally with Pytest

```bash
pytest -v tests/test_game.py
```

### Run in Docker (Headless CI Mode)

```bash
docker build -t lcm-hero-tests .
docker run --rm lcm-hero-tests
```
