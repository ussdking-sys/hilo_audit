#!/usr/bin/env python3
"""
BC.Game Hilo Provably Fair Audit & Simulation Tool — v1.3
==========================================================
Replicates BC.Game's Hilo provably fair card generation system.
Supports session verification, simulation, batch auditing, and
in-app reference for game rules + script usage.

v1.3: Corrected HMAC message format to match BC.Game's official spec:
    hash = HMAC_SHA256(clientSeed:nonce:round, serverSeed)
where 'round' is the card index within a single Hilo session.

Usage:
    python hilo_audit.py
"""

import hmac
import hashlib
import secrets
import os
import sys
import csv
import json
from typing import Optional

# ─── ANSI Color Codes ────────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"
    BG_DARK = "\033[40m"

def supports_color():
    """Check if terminal supports ANSI color codes."""
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

USE_COLOR = supports_color()

def clr(text, *codes):
    if not USE_COLOR:
        return text
    return "".join(codes) + str(text) + C.RESET

# ─── Card Definitions ─────────────────────────────────────────────────────────
# Ranks: index 0 = Ace (lowest), index 12 = King (highest)
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
RANK_NAMES = {
    'A': 'Ace', '2': '2', '3': '3', '4': '4', '5': '5',
    '6': '6', '7': '7', '8': '8', '9': '9', '10': '10',
    'J': 'Jack', 'Q': 'Queen', 'K': 'King'
}
SUITS = ['♠', '♥', '♦', '♣']
SUIT_COLORS = {'♠': C.WHITE, '♥': C.RED, '♦': C.RED, '♣': C.WHITE}

HOUSE_EDGE = 0.02  # 2%
NUM_RANKS = 13

def card_display(rank: str, suit: str) -> str:
    suit_color = SUIT_COLORS.get(suit, C.WHITE) if USE_COLOR else ""
    return clr(f"{rank}{suit}", C.BOLD, suit_color)

def rank_full(rank: str) -> str:
    return RANK_NAMES.get(rank, rank)

# ─── Provably Fair Core ───────────────────────────────────────────────────────
def derive_card(server_seed: str, client_seed: str, nonce: int, round_idx: int = 0) -> tuple[int, str, str]:
    """
    Derive a card from seeds using HMAC-SHA256.
    Returns (rank_index, rank, suit)

    BC.Game's official formula (per Help Center):
        hash = HMAC_SHA256(clientSeed:nonce:round, serverSeed)

    Where:
        • serverSeed  = HMAC key
        • clientSeed:nonce:round = HMAC message
        • nonce  = bet counter (increments per bet placed)
        • round  = card index WITHIN a single Hilo session (0, 1, 2, ...)
                   Each new card drawn in the same session uses the same
                   nonce but increments round.

    The first 4 bytes (8 hex chars) of the digest are read as a uint32,
    then mapped to a 52-card deck index. Rank = index % 13, Suit = index // 13.
    """
    message = f"{client_seed}:{nonce}:{round_idx}".encode('utf-8')
    key = server_seed.encode('utf-8')
    h = hmac.new(key, message, hashlib.sha256).hexdigest()

    # First 4 bytes → uint32, then map to deck index 0–51
    chunk = int(h[0:8], 16)
    index = chunk % 52
    rank_idx = index % NUM_RANKS
    suit_idx = (index // NUM_RANKS) % 4
    return rank_idx, RANKS[rank_idx], SUITS[suit_idx]

def hash_server_seed(server_seed: str) -> str:
    """SHA256 hash of server seed (what BC.Game shows publicly before reveal)."""
    return hashlib.sha256(server_seed.encode('utf-8')).hexdigest()

# ─── Payout Calculations ──────────────────────────────────────────────────────
def calc_probabilities(rank_idx: int) -> dict:
    """
    Calculate HI/LO/SAME probabilities for a given rank index.
    With unlimited decks: probability is based purely on rank distribution.
    """
    # Cards strictly lower (rank indices 0 to rank_idx-1)
    lo_count = rank_idx          # cards with rank < current
    # Cards strictly higher (rank indices rank_idx+1 to 12)
    hi_count = NUM_RANKS - 1 - rank_idx
    same_count = 1               # same rank (always possible with unlimited decks)

    # With unlimited decks, each rank has equal probability
    lo_prob  = lo_count  / NUM_RANKS
    hi_prob  = hi_count  / NUM_RANKS
    same_prob = same_count / NUM_RANKS

    return {
        'lo_prob':   lo_prob,
        'hi_prob':   hi_prob,
        'same_prob': same_prob,
        'lo_count':  lo_count,
        'hi_count':  hi_count,
    }

def calc_payout(probability: float) -> float:
    """
    Payout multiplier = (1 / probability) * (1 - house_edge)
    Returns 0 if probability is 0 (impossible bet).
    """
    if probability <= 0:
        return 0.0
    return round((1.0 / probability) * (1.0 - HOUSE_EDGE), 4)

def get_payouts(rank_idx: int) -> dict:
    probs = calc_probabilities(rank_idx)
    lo_pay  = calc_payout(probs['lo_prob'])
    hi_pay  = calc_payout(probs['hi_prob'])
    return {**probs, 'lo_payout': lo_pay, 'hi_payout': hi_pay}

# ─── Display Helpers ──────────────────────────────────────────────────────────
BANNER = r"""
  _   _ _ _         _             _ _ _   
 | | | (_) | ___   / \  _   _  __| (_) |_ 
 | |_| | | |/ _ \ / _ \| | | |/ _` | | __|
 |  _  | | | (_) / ___ \ |_| | (_| | | |_ 
 |_| |_|_|_|\___/_/   \_\__,_|\__,_|_|\__|
"""

def print_banner():
    print(clr(BANNER, C.CYAN, C.BOLD))
    print(clr("  BC.Game Hilo — Provably Fair Audit & Simulation Tool  v1.3", C.GRAY))
    print(clr("  House Edge: 2.00%  |  RTP: 98%  |  Ranks: A–K (13)", C.GRAY))
    print()

def print_separator(char="─", width=52):
    print(clr(char * width, C.GRAY))

def print_card_row(nonce, round_idx, card_rank, card_suit, rank_idx, payouts, guess=None, actual_next=None):
    card = card_display(card_rank, card_suit)
    lo_p  = f"{payouts['lo_prob']*100:5.1f}%"
    hi_p  = f"{payouts['hi_prob']*100:5.1f}%"
    lo_x  = f"{payouts['lo_payout']:.3f}x"
    hi_x  = f"{payouts['hi_payout']:.3f}x"

    rank_label = clr(f"{rank_full(card_rank):<6}", C.YELLOW)
    pos_label  = clr(f"n{nonce:<5} r{round_idx:<3}", C.GRAY)

    lo_str = clr(f"LO {lo_p} → {lo_x:>8}", C.BLUE)
    hi_str = clr(f"HI {hi_p} → {hi_x:>8}", C.MAGENTA)

    result_str = ""
    if guess and actual_next is not None:
        next_idx = actual_next
        won = False
        if guess.upper() == 'HI' and next_idx > rank_idx:
            won = True
        elif guess.upper() == 'LO' and next_idx < rank_idx:
            won = True
        elif guess.upper() in ('HI', 'LO') and next_idx == rank_idx:
            won = False  # Exact same = loss unless "same" option

        result_str = clr(" ✓ WIN", C.GREEN, C.BOLD) if won else clr(" ✗ LOSS", C.RED, C.BOLD)

    print(f"  {pos_label} {card} {rank_label}  {lo_str}  {hi_str}{result_str}")

def print_round_header():
    h = f"  {'Nonce/Rnd':<11} {'Card':<8} {'Rank':<6}  {'LO Prob → Pay':>18}  {'HI Prob → Pay':>18}"
    print(clr(h, C.GRAY, C.DIM))
    print_separator()

# ─── Session Input ────────────────────────────────────────────────────────────
def prompt(label, default=None):
    suffix = f" [{clr(default, C.CYAN)}]" if default else ""
    val = input(f"  {clr('›', C.GREEN)} {label}{suffix}: ").strip()
    return val if val else default

def get_session_inputs(allow_random=True):
    print()
    print(clr("  ── Session Seeds ──────────────────────────────", C.CYAN))
    print(clr("  Leave blank to auto-generate random seeds.", C.GRAY) if allow_random else "")
    print()

    server_seed = prompt("Server Seed (plain text, not hash)")
    if not server_seed:
        server_seed = secrets.token_hex(32)
        print(clr(f"  Generated: {server_seed}", C.GRAY))

    client_seed = prompt("Client Seed")
    if not client_seed:
        client_seed = secrets.token_urlsafe(16)
        print(clr(f"  Generated: {client_seed}", C.GRAY))

    nonce_str = prompt("Starting Nonce", default="1")
    try:
        nonce = int(nonce_str)
    except (ValueError, TypeError):
        nonce = 1

    return server_seed, client_seed, nonce

# ─── Mode 1: Verify / Reconstruct Session ────────────────────────────────────
def mode_verify():
    print()
    print(clr("  ══ VERIFY SESSION ══════════════════════════════", C.CYAN, C.BOLD))
    print(clr("  Reconstruct your exact session card sequence.", C.GRAY))
    print(clr("  Each Hilo bet uses ONE nonce. Within that bet, each", C.GRAY))
    print(clr("  card drawn increments the round (0, 1, 2, ...).", C.GRAY))

    server_seed, client_seed, nonce = get_session_inputs(allow_random=False)

    rounds_str = prompt("How many cards/rounds to display (within this nonce)", default="10")
    try:
        rounds = max(1, int(rounds_str))
    except (ValueError, TypeError):
        rounds = 10

    print()
    print(clr(f"  Server Seed Hash: {hash_server_seed(server_seed)}", C.GRAY))
    print(clr(f"  Client Seed:      {client_seed}", C.GRAY))
    print(clr(f"  Nonce:            {nonce}", C.GRAY))
    print()
    print_round_header()

    results = []
    for r in range(rounds):
        rank_idx, rank, suit = derive_card(server_seed, client_seed, nonce, r)
        payouts = get_payouts(rank_idx)
        print_card_row(nonce, r, rank, suit, rank_idx, payouts)
        results.append({
            'nonce': nonce, 'round': r, 'rank': rank, 'suit': suit,
            'rank_idx': rank_idx, **payouts
        })

    print_separator()
    _offer_export(results, server_seed, client_seed)

# ─── Mode 2: Simulate ─────────────────────────────────────────────────────────
def mode_simulate():
    print()
    print(clr("  ══ SIMULATION MODE ═════════════════════════════", C.CYAN, C.BOLD))
    print(clr("  Simulate cards drawn within ONE Hilo bet (nonce).", C.GRAY))
    print(clr("  In Hilo, one bet draws many cards (round 0,1,2,...).", C.GRAY))

    server_seed, client_seed, nonce = get_session_inputs()

    rounds_str = prompt("Number of cards to draw in this session", default="20")
    try:
        rounds = max(1, int(rounds_str))
    except (ValueError, TypeError):
        rounds = 20

    guess_mode = prompt("Enter guess per card? (y/n)", default="n")
    auto_guess = guess_mode.lower() != 'y'

    print()
    print(clr(f"  Server Seed Hash: {hash_server_seed(server_seed)}", C.GRAY))
    print(clr(f"  Nonce:            {nonce}", C.GRAY))
    print()
    print_round_header()

    results = []
    wins = 0
    total_guessed = 0
    payout_sum = 0.0

    for r in range(rounds):
        rank_idx, rank, suit = derive_card(server_seed, client_seed, nonce, r)
        payouts = get_payouts(rank_idx)

        # Peek next card for win/loss resolution
        next_rank_idx, _, _ = derive_card(server_seed, client_seed, nonce, r + 1)

        guess = None
        if not auto_guess:
            print_card_row(nonce, r, rank, suit, rank_idx, payouts)
            guess = prompt(f"  Your guess for next card (hi/lo/skip)", default="skip")
            if guess.lower() == 'skip':
                guess = None

        if guess:
            total_guessed += 1
            won = (guess.upper() == 'HI' and next_rank_idx > rank_idx) or \
                  (guess.upper() == 'LO' and next_rank_idx < rank_idx)
            if won:
                wins += 1
                pay = payouts['hi_payout'] if guess.upper() == 'HI' else payouts['lo_payout']
                payout_sum += pay
            print_card_row(nonce, r, rank, suit, rank_idx, payouts, guess, next_rank_idx)
        else:
            print_card_row(nonce, r, rank, suit, rank_idx, payouts)

        results.append({
            'nonce': nonce, 'round': r, 'rank': rank, 'suit': suit,
            'rank_idx': rank_idx, 'guess': guess or '', **payouts
        })

    print_separator()

    # Summary
    if total_guessed > 0:
        print()
        print(clr("  ── Session Summary ─────────────────────────────", C.CYAN))
        win_rate = wins / total_guessed * 100
        avg_pay  = payout_sum / wins if wins > 0 else 0
        print(f"  Cards guessed  : {clr(total_guessed, C.WHITE)}")
        print(f"  Wins           : {clr(wins, C.GREEN)}  |  Losses: {clr(total_guessed - wins, C.RED)}")
        print(f"  Win Rate       : {clr(f'{win_rate:.1f}%', C.YELLOW)}")
        print(f"  Avg Payout (W) : {clr(f'{avg_pay:.3f}x', C.CYAN)}")
        print_separator()

    _offer_export(results, server_seed, client_seed)

# ─── Mode 4: Batch Verify ─────────────────────────────────────────────────────
def mode_batch():
    print()
    print(clr("  ══ BATCH VERIFY ════════════════════════════════", C.CYAN, C.BOLD))
    print(clr("  Load a JSON or CSV file of rounds to verify.", C.GRAY))
    print(clr("  Required fields: server_seed, client_seed, nonce, round", C.GRAY))
    print(clr("  Optional field:  expected_rank  (A, 2-10, J, Q, K)", C.GRAY))
    print()

    filepath = prompt("File path (JSON or CSV)")
    if not filepath or not os.path.exists(filepath):
        print(clr("  ✗ File not found.", C.RED))
        return

    rounds = []
    try:
        if filepath.endswith('.json'):
            with open(filepath, 'r') as f:
                rounds = json.load(f)
        elif filepath.endswith('.csv'):
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row['nonce'] = int(row['nonce'])
                    row['round'] = int(row.get('round', 0))
                    rounds.append(row)
        else:
            print(clr("  ✗ Unsupported file format. Use .json or .csv", C.RED))
            return
    except Exception as e:
        print(clr(f"  ✗ Error reading file: {e}", C.RED))
        return

    print()
    print(clr(f"  Loaded {len(rounds)} rounds.", C.GRAY))
    print_round_header()

    matches = 0
    for r in rounds:
        ss  = r.get('server_seed', '')
        cs  = r.get('client_seed', '')
        non = int(r.get('nonce', 1))
        rnd = int(r.get('round', 0))
        exp = r.get('expected_rank', '').upper()

        rank_idx, rank, suit = derive_card(ss, cs, non, rnd)
        payouts = get_payouts(rank_idx)

        match = (rank == exp) if exp else None
        if match:
            matches += 1

        match_str = ""
        if match is True:
            match_str = clr(" ✓ MATCH", C.GREEN)
        elif match is False:
            match_str = clr(f" ✗ MISMATCH (expected {exp})", C.RED)

        print_card_row(non, rnd, rank, suit, rank_idx, payouts)
        if match_str:
            print(f"         {match_str}")

    print_separator()
    if any(r.get('expected_rank') for r in rounds):
        total_checked = sum(1 for r in rounds if r.get('expected_rank'))
        print(clr(f"  Matched {matches}/{total_checked} rounds.", C.CYAN))

# ─── Mode 3: Single Round Lookup ──────────────────────────────────────────────
def mode_single():
    print()
    print(clr("  ══ SINGLE ROUND LOOKUP ═════════════════════════", C.CYAN, C.BOLD))
    print(clr("  Derive the exact card for a specific nonce + round.", C.GRAY))

    server_seed, client_seed, nonce = get_session_inputs(allow_random=False)

    round_str = prompt("Round (0 = first card of the session)", default="0")
    try:
        round_idx = max(0, int(round_str))
    except (ValueError, TypeError):
        round_idx = 0

    rank_idx, rank, suit = derive_card(server_seed, client_seed, nonce, round_idx)
    payouts = get_payouts(rank_idx)

    print()
    print(clr("  ── Result ──────────────────────────────────────", C.CYAN))
    print(f"  Card       : {card_display(rank, suit)}  {clr(rank_full(rank), C.YELLOW)}")
    print(f"  Position   : nonce {clr(nonce, C.WHITE)}  /  round {clr(round_idx, C.WHITE)}")
    print(f"  Rank Index : {clr(rank_idx, C.WHITE)} / 12  (0=Ace, 12=King)")
    print(f"  Server Hash: {clr(hash_server_seed(server_seed), C.GRAY)}")
    print()
    lo_pct  = f"{payouts['lo_prob']*100:.1f}%"
    hi_pct  = f"{payouts['hi_prob']*100:.1f}%"
    sa_pct  = f"{payouts['same_prob']*100:.1f}%"
    lo_pay  = f"{payouts['lo_payout']:.4f}x"
    hi_pay  = f"{payouts['hi_payout']:.4f}x"
    print(f"  LO odds    : {clr(lo_pct, C.BLUE)}  →  payout {clr(lo_pay, C.CYAN)}")
    print(f"  HI odds    : {clr(hi_pct, C.MAGENTA)}  →  payout {clr(hi_pay, C.CYAN)}")
    print(f"  SAME prob  : {clr(sa_pct, C.GRAY)}")
    print_separator()

# ─── Export Helper ────────────────────────────────────────────────────────────
def _offer_export(results, server_seed, client_seed):
    ans = prompt("Export results to CSV? (y/n)", default="n")
    if ans and ans.lower() == 'y':
        fname = prompt("Output filename", default="hilo_session.csv")
        try:
            with open(fname, 'w', newline='') as f:
                fieldnames = ['nonce', 'round', 'rank', 'suit', 'rank_idx',
                              'lo_prob', 'hi_prob', 'same_prob',
                              'lo_payout', 'hi_payout', 'lo_count', 'hi_count']
                if 'guess' in results[0]:
                    fieldnames.append('guess')
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(results)
            print(clr(f"  ✓ Saved to {fname}", C.GREEN))
        except Exception as e:
            print(clr(f"  ✗ Export failed: {e}", C.RED))

# ─── Mode 5: Game Rules ───────────────────────────────────────────────────────
def mode_rules():
    print()
    print(clr("  ══ HILO — GAME RULES ═══════════════════════════", C.CYAN, C.BOLD))
    print()

    print(clr("  THE GOAL", C.YELLOW, C.BOLD))
    print("    Guess whether the next card will be HIGHER or LOWER")
    print("    than the card currently showing. Correct = you win.")
    print("    Wrong = you lose your bet.")
    print()

    print(clr("  CARD RANKING  (low → high)", C.YELLOW, C.BOLD))
    print(clr("    Ace  2  3  4  5  6  7  8  9  10  J  Q  K", C.WHITE, C.BOLD))
    print("    13 ranks total. Ace is the LOWEST card. King is the HIGHEST.")
    print()

    print(clr("  HOW A ROUND WORKS", C.YELLOW, C.BOLD))
    print("    1. You place a bet.")
    print("    2. A starting card is revealed face-up.")
    print("    3. You choose HI (next will be higher) or LO (next lower).")
    print("    4. Next card is revealed → you win or lose.")
    print("    5. If you win, you can CASH OUT or keep going for a")
    print("       bigger multiplier. Each correct guess stacks the payout.")
    print()

    print(clr("  PAYOUTS", C.YELLOW, C.BOLD))
    print("    Payouts depend on how likely your guess is.")
    print("    • Easy guesses (e.g. \"higher than a 2\") pay very little.")
    print("    • Hard guesses (e.g. \"higher than a King\") pay a lot — or")
    print("      are impossible (King has nothing higher).")
    print()
    print("    Formula:")
    print(clr("      payout = (1 / probability) × (1 - 0.02)", C.CYAN))
    print("    The 0.02 is the 2% house edge (RTP = 98%).")
    print()

    print(clr("  THE \"SAME\" CASE", C.YELLOW, C.BOLD))
    print("    BC.Game uses unlimited decks, so the next card can be")
    print("    the SAME rank as the current one. Because of this:")
    print("    • \"Higher or same\" and \"Lower or same\" bets exist.")
    print("    • If the same card is drawn again, either HI or LO wins —")
    print("      UNLESS the current card is an Ace (nothing lower) or")
    print("      a King (nothing higher).")
    print()

    print(clr("  SKIP", C.YELLOW, C.BOLD))
    print("    You can skip a card and get a new one without betting.")
    print("    Skips can be used multiple times per session.")
    print()

    print(clr("  PROVABLY FAIR", C.YELLOW, C.BOLD))
    print("    Each card is generated from FOUR values:")
    print(clr("      • Server Seed   ", C.CYAN) + "(hidden until reveal, hashed beforehand)")
    print(clr("      • Client Seed   ", C.CYAN) + "(you can set this yourself)")
    print(clr("      • Nonce         ", C.CYAN) + "(bet counter — increments each new BET)")
    print(clr("      • Round         ", C.CYAN) + "(card counter — increments each card")
    print(clr("                       drawn WITHIN the same bet)", C.CYAN))
    print()
    print("    BC.Game's formula:")
    print(clr("      hash = HMAC_SHA256(clientSeed:nonce:round, serverSeed)", C.CYAN))
    print()
    print("    A single Hilo bet draws many cards (round 0, 1, 2, ...).")
    print("    When you cash out or lose, the nonce increments for the")
    print("    next bet and round resets to 0.")
    print()
    print("    Once the round ends and the server seed is revealed, you")
    print("    can plug all four values into THIS tool to verify outcomes.")
    print_separator()

# ─── Mode 6: Script Usage ─────────────────────────────────────────────────────
def mode_usage():
    print()
    print(clr("  ══ HOW TO USE THIS SCRIPT ══════════════════════", C.CYAN, C.BOLD))
    print()

    print(clr("  QUICK START", C.YELLOW, C.BOLD))
    print("    Pick a mode from the main menu by typing its number.")
    print("    Press Enter at any prompt to use the default value")
    print(clr("    shown in [brackets].", C.GRAY))
    print()

    print(clr("  [1] VERIFY / RECONSTRUCT SESSION", C.GREEN, C.BOLD))
    print("    Use this AFTER a session to confirm BC.Game played fair.")
    print("    You need:")
    print("      • The plain server seed (revealed after seed rotation)")
    print("      • Your client seed")
    print("      • The nonce for the bet you want to audit")
    print("    The tool walks through rounds 0, 1, 2, ... within that nonce")
    print("    and prints the exact card sequence you should have seen.")
    print()

    print(clr("  [2] SIMULATE ROUNDS", C.GREEN, C.BOLD))
    print("    Simulate cards drawn within a single bet (nonce).")
    print("    • Leave seeds blank → tool generates random ones.")
    print("    • Choose \"y\" when asked if you want to guess each card")
    print("      to practice HI/LO decisions and see your win rate.")
    print("    • Useful for strategy testing without betting real money.")
    print()

    print(clr("  [3] SINGLE ROUND LOOKUP", C.GREEN, C.BOLD))
    print("    Derive ONE specific card from a specific nonce + round.")
    print("    Fastest mode if you only want to check one card.")
    print()

    print(clr("  [4] BATCH VERIFY FROM FILE", C.GREEN, C.BOLD))
    print("    Verify many cards at once from a .json or .csv file.")
    print("    File format (CSV):")
    print(clr("      server_seed,client_seed,nonce,round,expected_rank", C.GRAY))
    print(clr("      abc123...,myseed,1,0,K", C.GRAY))
    print(clr("      abc123...,myseed,1,1,7", C.GRAY))
    print()
    print("    Each row is checked against the algorithm.")
    print("    Results show ✓ MATCH or ✗ MISMATCH per row.")
    print()

    print(clr("  TIPS", C.YELLOW, C.BOLD))
    print("    • Press Ctrl+C any time to cancel back to the menu.")
    print("    • CSV exports work in Excel, Google Sheets, LibreOffice.")
    print("    • The server seed BC.Game shows DURING play is the HASH,")
    print("      not the plain seed. You only get the plain seed after")
    print("      you rotate/reset to a new server seed.")
    print()

    print(clr("  TERMUX NOTES", C.YELLOW, C.BOLD))
    print("    • Long output? Pipe to less:  python hilo_audit.py | less -R")
    print("    • Save a session log:         python hilo_audit.py > log.txt")
    print("    • No color in output? Your terminal may not support ANSI.")
    print_separator()

# ─── Main Menu ────────────────────────────────────────────────────────────────
MENU = [
    ("1", "Verify / Reconstruct Session",   mode_verify),
    ("2", "Simulate Rounds",                mode_simulate),
    ("3", "Single Round Lookup",            mode_single),
    ("4", "Batch Verify from File",         mode_batch),
    ("5", "Game Rules",                     mode_rules),
    ("6", "Script Usage Guide",             mode_usage),
    ("0", "Exit",                           None),
]

def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    print_banner()

    while True:
        print(clr("  ── Main Menu ───────────────────────────────────", C.CYAN))
        for key, label, _ in MENU:
            k = clr(f"[{key}]", C.GREEN, C.BOLD)
            print(f"  {k} {label}")
        print()

        choice = input(clr("  › Choose: ", C.GREEN)).strip()
        print()

        matched = False
        for key, _, fn in MENU:
            if choice == key:
                matched = True
                if fn is None:
                    print(clr("  Goodbye.\n", C.GRAY))
                    sys.exit(0)
                fn()
                print()
                break

        if not matched:
            print(clr("  Invalid choice. Try again.", C.RED))

if __name__ == "__main__":
    main()
