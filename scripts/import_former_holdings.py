"""
One-time script to import former stock holdings into the net worth system.

Creates net worth assets and monthly snapshots for:
1. ESI.PA (ESI Group) — EUR, real daily prices from CSV
2. Netlight — SEK, linear interpolation between known data points

Run from repo root:
    .venv/bin/python scripts/import_former_holdings.py
"""

import csv
import sqlite3
import os
from datetime import datetime, date
from collections import defaultdict

# ─── Configuration ──────────────────────────────────────────────

DB_PATH = os.environ.get(
    'PORTFOLIO_DB_PATH',
    os.path.join(os.path.dirname(__file__), '..', 'data', 'portfolio.db')
)

ESI_CSV_PATH = os.path.expanduser(
    "~/Downloads/ESI.PA_MAX_1DAY_FROM_PERPLEXITY.csv"
)

# ESI.PA — 93 shares, EUR
ESI_SHARES = 93
ESI_BUY_DATE = date(2019, 12, 13)
ESI_SELL_DATE = date(2024, 1, 24)
ESI_ASSET_ID = "esi"
ESI_LABEL = "ESI Group"

# Netlight — SEK, two tranches
NETLIGHT_TRANCHES = [
    {"date": date(2023, 6, 1), "shares": 200, "price": 50.0},
    {"date": date(2024, 10, 1), "shares": 420, "price": 47.62},
]
NETLIGHT_SELL_DATE = date(2025, 7, 1)
NETLIGHT_SELL_PRICE = 47.62
NETLIGHT_ASSET_ID = "netlight"
NETLIGHT_LABEL = "Netlight"


# ─── Helpers ────────────────────────────────────────────────────

def get_connection(db_path):
    return sqlite3.connect(db_path)


def add_asset(conn, asset_id, label, current_value=0.0):
    """Create a net worth asset (skip if already exists)."""
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        conn.execute(
            "INSERT INTO net_worth_assets (id, label, current_value, updated_at) VALUES (?, ?, ?, ?)",
            (asset_id, label, current_value, today)
        )
        conn.commit()
        print(f"  Created asset: {asset_id} ({label})")
    except sqlite3.IntegrityError:
        print(f"  Asset '{asset_id}' already exists, skipping creation")


def add_snapshot(conn, date_str, asset_id, value):
    """Upsert a net worth snapshot."""
    conn.execute(
        "INSERT INTO net_worth_snapshots (date, asset_id, value) VALUES (?, ?, ?) "
        "ON CONFLICT(date, asset_id) DO UPDATE SET value = excluded.value",
        (date_str, asset_id, value)
    )


def get_fx_lookup(conn, pair, end_date_str):
    """Build date→rate dict for a currency pair."""
    cursor = conn.execute(
        "SELECT date, rate FROM fx_rates_history WHERE pair = ? AND date <= ? ORDER BY date ASC",
        (pair, end_date_str)
    )
    return {row[0]: row[1] for row in cursor.fetchall()}


def forward_fill_fx(fx_lookup, date_str):
    """Get the FX rate for a date, forward-filling from the last known rate."""
    if date_str in fx_lookup:
        return fx_lookup[date_str]
    # Find the most recent rate before this date
    best_rate = None
    for d, rate in fx_lookup.items():
        if d <= date_str:
            best_rate = rate
    return best_rate or 1.0


def last_day_of_month(d):
    """Return the last day of the month for a given date."""
    if d.month == 12:
        return date(d.year + 1, 1, 1).replace(day=1) - __import__('datetime').timedelta(days=1)
    return date(d.year, d.month + 1, 1) - __import__('datetime').timedelta(days=1)


def monthly_end_dates(start, end):
    """Generate last-day-of-month dates between start and end (inclusive)."""
    dates = []
    current = last_day_of_month(start)
    while current <= end:
        dates.append(current)
        # Move to next month
        if current.month == 12:
            current = last_day_of_month(date(current.year + 1, 1, 1))
        else:
            current = last_day_of_month(date(current.year, current.month + 1, 1))
    return dates


# ─── ESI.PA Import ──────────────────────────────────────────────

def import_esi(conn):
    print("\n=== Importing ESI.PA (ESI Group) ===")

    # Parse CSV
    prices = {}  # date_str → close price
    with open(ESI_CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse ISO date: "2024-01-24T00:00:00+01:00" → "2024-01-24"
            date_str = row['date'][:10]
            close = float(row['close'])
            prices[date_str] = close

    print(f"  Parsed {len(prices)} daily prices from CSV")

    # Filter to holding period
    buy_str = ESI_BUY_DATE.isoformat()
    sell_str = ESI_SELL_DATE.isoformat()
    holding_prices = {d: p for d, p in prices.items() if buy_str <= d <= sell_str}
    print(f"  {len(holding_prices)} prices in holding period ({buy_str} → {sell_str})")

    # Group by month, take last available close
    monthly = defaultdict(list)
    for d, p in holding_prices.items():
        month_key = d[:7]  # "YYYY-MM"
        monthly[month_key].append((d, p))

    monthly_prices = {}
    for month_key, entries in monthly.items():
        entries.sort()
        last_date, last_price = entries[-1]  # Last trading day of the month
        monthly_prices[last_date] = last_price

    # Create asset and insert snapshots
    add_asset(conn, ESI_ASSET_ID, ESI_LABEL, current_value=0.0)

    count = 0
    for date_str in sorted(monthly_prices.keys()):
        value = ESI_SHARES * monthly_prices[date_str]
        add_snapshot(conn, date_str, ESI_ASSET_ID, round(value, 2))
        count += 1

    conn.commit()
    print(f"  Inserted {count} monthly snapshots")

    # Show first and last
    first_date = min(monthly_prices.keys())
    last_date = max(monthly_prices.keys())
    print(f"  First: {first_date} @ €{monthly_prices[first_date]:.2f}/share = €{ESI_SHARES * monthly_prices[first_date]:.2f}")
    print(f"  Last:  {last_date} @ €{monthly_prices[last_date]:.2f}/share = €{ESI_SHARES * monthly_prices[last_date]:.2f}")


# ─── Netlight Import ────────────────────────────────────────────

def import_netlight(conn):
    print("\n=== Importing Netlight ===")

    # Build the timeline of shares held and price points
    # Tranche 1: 2023-06-01, 200 shares @ 50 SEK
    # Tranche 2: 2024-10-01, +420 shares @ 47.62 SEK (total 620)
    # Sell:      2025-07-01, all 620 shares @ 47.62 SEK

    start_date = NETLIGHT_TRANCHES[0]["date"]
    end_date = NETLIGHT_SELL_DATE

    # Get FX rates
    fx_lookup = get_fx_lookup(conn, "SEKEUR", end_date.isoformat())
    if not fx_lookup:
        print("  WARNING: No SEKEUR FX rates found! Using rate=1.0")
    else:
        print(f"  Loaded {len(fx_lookup)} SEKEUR FX rates")

    # Create asset
    add_asset(conn, NETLIGHT_ASSET_ID, NETLIGHT_LABEL, current_value=0.0)

    # Generate monthly snapshots
    month_dates = monthly_end_dates(start_date, end_date)
    count = 0

    for md in month_dates:
        md_str = md.isoformat()

        # Determine shares and price at this date
        if md < NETLIGHT_TRANCHES[1]["date"]:
            # Period 1: 200 shares, price interpolates 50 → 47.62
            shares = 200
            total_days = (NETLIGHT_TRANCHES[1]["date"] - start_date).days
            elapsed = (md - start_date).days
            t = elapsed / total_days if total_days > 0 else 0
            price_sek = 50.0 + (47.62 - 50.0) * t
        else:
            # Period 2: 620 shares, price constant at 47.62
            shares = 620
            price_sek = 47.62

        value_sek = shares * price_sek
        fx_rate = forward_fill_fx(fx_lookup, md_str)
        value_eur = value_sek * fx_rate

        add_snapshot(conn, md_str, NETLIGHT_ASSET_ID, round(value_eur, 2))
        count += 1

    conn.commit()
    print(f"  Inserted {count} monthly snapshots")

    # Show first and last
    if month_dates:
        first = month_dates[0]
        last = month_dates[-1]
        first_fx = forward_fill_fx(fx_lookup, first.isoformat())
        last_fx = forward_fill_fx(fx_lookup, last.isoformat())
        print(f"  First: {first.isoformat()} — 200 shares @ ~50 SEK × {first_fx:.4f} FX")
        print(f"  Last:  {last.isoformat()} — 620 shares @ 47.62 SEK × {last_fx:.4f} FX")


# ─── Main ───────────────────────────────────────────────────────

def main():
    db_path = os.path.abspath(DB_PATH)
    print(f"Database: {db_path}")

    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        return

    conn = get_connection(db_path)
    try:
        import_esi(conn)
        import_netlight(conn)
        print("\nDone!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
