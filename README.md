# hilo-audit

**Version 1.4** — A provably fair audit and simulation tool for the **Hilo** card prediction game on [BC.Game](https://bc.game).

Replicates BC.Game's HMAC-SHA256 seed derivation algorithm locally, allowing you to reconstruct past sessions, verify card outcomes, and run simulations — all from your terminal with zero external dependencies.

---

## Changelog

### v1.4
**Simulate mode input validation** — the guess prompt is now fully guarded against bad input.

- **Invalid input rejected** — entering anything other than `hi`, `lo`, or `skip` now shows an error and re-prompts instead of silently recording a loss.
- **Impossible bets blocked** — betting `lo` on an Ace (nothing lower, 0× payout) or `hi` on a King (nothing higher, 0× payout) is rejected with a clear explanation before the guess is committed:
  ```
  ✗ LO is impossible on a Ace (nothing lower). Choose hi or skip.
  ✗ HI is impossible on a King (nothing higher). Choose lo or skip.
  ```
  Previously both were silently accepted and counted as losses with no warning to the user.

---

### v1.3
**Algorithm correction** — verified against BC.Game's official Help Center spec.

Previous versions used `HMAC_SHA256(serverSeed, "clientSeed:nonce")`. The correct formula is:

```
hash = HMAC_SHA256(clientSeed:nonce:round, serverSeed)
```

The added **`round`** parameter is the card index *within* a single Hilo bet (0, 1, 2, ...). One bet draws many cards before cash-out or loss, all using the same nonce — round increments per card, nonce increments per new bet.

Other changes:
- All four modes (verify, simulate, single, batch) now use nonce + round correctly
- Batch verify CSV/JSON schema adds a `round` field
- CSV exports include a `round` column
- Updated in-app Game Rules and Usage Guide to reflect the new model
- Output rows now display `n<nonce> r<round>` so you can map results to bets cleanly

---

### v1.2
- **In-app Game Rules** — menu option `[5]` explains the rules of Hilo
- **In-app Usage Guide** — menu option `[6]` walks you through every mode

---

## Features

- **Verify Session** — Input your server seed, client seed, and nonce to reconstruct your exact card sequence (round 0, 1, 2, ...)
- **Simulate Rounds** — Run N rounds with optional per-card HI/LO guessing and a session summary
- **Single Round Lookup** — Derive the card and payout odds for any specific nonce + round
- **Batch Verify** — Load a `.json` or `.csv` file of past rounds and verify them all at once
- **Game Rules** — Built-in reference for how Hilo works
- **Script Usage Guide** — Built-in walkthrough of every mode
- **CSV Export** — Save any session's results to a spreadsheet
- **No dependencies** — Pure Python standard library (`hmac`, `hashlib`, `csv`, `json`, `secrets`)
- **Termux-friendly** — Runs on Android via Termux with no additional setup

---

## How Provably Fair Works

Per BC.Game's Help Center:

```
hash = HMAC_SHA256(clientSeed:nonce:round, serverSeed)
```

Where:
- **serverSeed** is the HMAC key
- **clientSeed:nonce:round** is the HMAC message
- **nonce** increments each new bet
- **round** increments each card drawn within the same bet (starts at 0)

The first 4 bytes of the hex digest are mapped to a card index (0–51), giving a rank (0–12, Ace to King) and a suit. BC.Game shows you the *hashed* server seed before play. After you rotate to a new server seed, the previous plain seed is revealed — that's when you use this tool.

**Card ranking (low → high):**

```
Ace → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → Jack → Queen → King
```

**Payout formula:**

```
payout = (1 / probability) × (1 - house_edge)
house_edge = 2%  |  RTP = 98%
```

---

## Requirements

- Python 3.10 or higher
- No pip installs required

---

## Installation

**Standard (Linux / macOS / Windows):**

```bash
git clone https://github.com/yourusername/hilo-audit.git
cd hilo-audit
python3 hilo_audit.py
```

**Termux (Android):**

```bash
pkg update && pkg install python git
git clone https://github.com/yourusername/hilo-audit.git
cd hilo-audit
python hilo_audit.py
```

---

## Usage

Launch the tool and select a mode from the interactive menu:

```
  [1] Verify / Reconstruct Session
  [2] Simulate Rounds
  [3] Single Round Lookup
  [4] Batch Verify from File
  [5] Game Rules
  [6] Script Usage Guide
  [0] Exit
```

> **Tip:** New to Hilo or the script? Pick `[5]` first to learn the game, then `[6]` to see what each mode does.

### Mode 1 — Verify Session

Enter your seeds and nonce to walk through every card drawn in that bet (round 0, 1, 2, ...). BC.Game reveals the plain server seed once you rotate to a new one.

```
  › Server Seed (plain text, not hash): <revealed by BC.Game after rotation>
  › Client Seed:                        YpGXd1BikPaWmYc8k
  › Starting Nonce:                     3037
  › How many cards/rounds to display:   10
```

### Mode 2 — Simulate

Generate or enter seeds and simulate cards drawn within a single bet. Optionally guess HI/LO each card to track win rate and average payout.

### Mode 3 — Single Round Lookup

Derive the exact card and full probability/payout breakdown for one specific (nonce, round) pair.

### Mode 4 — Batch Verify

Provide a `.json` or `.csv` file listing past rounds with expected cards:

**JSON format:**
```json
[
  {
    "server_seed": "your_plain_server_seed",
    "client_seed": "YpGXd1BikPaWmYc8k",
    "nonce": 3037,
    "round": 0,
    "expected_rank": "Q"
  }
]
```

**CSV format:**
```
server_seed,client_seed,nonce,round,expected_rank
your_plain_server_seed,YpGXd1BikPaWmYc8k,3037,0,Q
your_plain_server_seed,YpGXd1BikPaWmYc8k,3037,1,7
```

### Mode 5 — Game Rules

Built-in explanation of how Hilo works: card ranking, betting, payouts, the "same card" case, skips, and the provably fair model. No internet required.

### Mode 6 — Script Usage Guide

Built-in walkthrough of every mode with examples and Termux tips (piping to `less`, saving logs, etc.).

---

## Project Structure

```
hilo-audit/
├── hilo_audit.py
├── README.md
├── LICENSE
└── .gitignore
```

---

## Disclaimer

This tool is intended for **auditing and verification purposes only**. It does not interact with BC.Game's servers, place bets, or automate gameplay. Past results can only be fully verified after BC.Game reveals the plain server seed at the end of a session.

Gambling involves financial risk. This tool does not guarantee future outcomes.

---

## License

MIT — see [LICENSE](LICENSE)
