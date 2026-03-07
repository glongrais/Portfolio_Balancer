#!/usr/bin/env python3
"""
One-time import script for Crypto portfolio (portfolio_id=4) transactions
from a CSV file with BTC transactions (BUY + STACK/STAKING).

Usage:
    cd stock_portfolio_app
    ../.venv/bin/python scripts/import_crypto_csv.py ../Crypto-Transactions.csv
    ../.venv/bin/python scripts/import_crypto_csv.py ../Crypto-Transactions.csv --dry-run --verbose
"""

import argparse
import csv
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import yfinance as yf

PORTFOLIO_ID = 4
SYMBOL_CSV = "BTC"
SYMBOL_DB = "BTC-EUR"
LOGO_URL_TEMPLATE = "https://api.elbstream.com/logos/symbol/{symbol}?format=png&size=128"


def get_db_path(override=None):
    if override:
        return override
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.environ.get('PORTFOLIO_DB_PATH', os.path.join(project_root, 'data', 'portfolio.db'))


def parse_number(s):
    """Parse European number format: '50,00 €' or '98 658,25 €' -> float. Returns None if empty."""
    s = s.strip()
    if not s:
        return None
    s = s.replace('€', '').replace('\xa0', '').replace(' ', '').replace(',', '.')
    if not s:
        return None
    return float(s)


def parse_csv(filepath):
    """Parse the crypto CSV into a list of dicts."""
    rows = []
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader)
        assert header == ['Date', 'Type', 'Symbol', 'Amount €', 'Amount Token', 'PRU €'], \
            f"Unexpected CSV header: {header}"

        for i, row in enumerate(reader):
            date_str, txn_type, symbol, amount_eur_str, amount_token_str, pru_eur_str = row
            date = date_str.replace('/', '-')
            amount_eur = parse_number(amount_eur_str)
            amount_token = parse_number(amount_token_str)
            pru_eur = parse_number(pru_eur_str)

            rows.append({
                'csv_index': i,
                'date': date,
                'type': txn_type,
                'symbol': symbol,
                'amount_eur': amount_eur,
                'amount_token': amount_token,
                'pru_eur': pru_eur,
            })

    return rows


def ensure_stock_exists(conn, dry_run=False, verbose=False):
    """Ensure BTC-EUR exists in the stocks table. Returns stockid."""
    row = conn.execute("SELECT stockid FROM stocks WHERE symbol = ?", (SYMBOL_DB,)).fetchone()
    if row:
        if verbose:
            print(f"  Stock {SYMBOL_DB} already exists (stockid={row[0]})")
        return row[0]

    if dry_run:
        print(f"  [DRY-RUN] Would insert stock {SYMBOL_DB} (fetching metadata from yfinance)")
        info = yf.Ticker(SYMBOL_DB).info
        print(f"    -> {info.get('longName', '?')}, currency={info.get('currency', '?')}")
        return -1

    print(f"  Inserting stock {SYMBOL_DB}...")
    info = yf.Ticker(SYMBOL_DB).info
    conn.execute('''
        INSERT INTO stocks (symbol, name, price, currency, market_cap, sector, industry, country, logo_url, quote_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            name=excluded.name, price=excluded.price, currency=excluded.currency,
            market_cap=excluded.market_cap, sector=excluded.sector, industry=excluded.industry,
            country=excluded.country, logo_url=excluded.logo_url, quote_type=excluded.quote_type
    ''', (
        SYMBOL_DB,
        info.get("longName", ""),
        info.get("currentPrice", info.get("previousClose")),
        info.get("currency", "EUR"),
        info.get("marketCap"),
        info.get("sector", ""),
        info.get("industry", ""),
        info.get("country", ""),
        LOGO_URL_TEMPLATE.format(symbol=SYMBOL_DB),
        info.get("quoteType", "CRYPTOCURRENCY"),
    ))
    conn.commit()

    row = conn.execute("SELECT stockid FROM stocks WHERE symbol = ?", (SYMBOL_DB,)).fetchone()
    print(f"    -> stockid={row[0]}, name={info.get('longName', '?')}")
    return row[0]


def load_existing_transactions(conn, csv_row_count):
    """Load pre-import state, compute base_rowid for idempotent imports."""
    total = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE portfolioid = ?", (PORTFOLIO_ID,)
    ).fetchone()[0]

    max_rowid = conn.execute(
        "SELECT COALESCE(MAX(rowid), 0) FROM transactions WHERE portfolioid = ?", (PORTFOLIO_ID,)
    ).fetchone()[0]

    if total > csv_row_count:
        pre_existing_count = total - csv_row_count
        base_rowid = pre_existing_count
    elif total > 0:
        # Some rows already imported — base_rowid aligns with existing convention
        base_rowid = 1
    else:
        base_rowid = max_rowid + 1

    return base_rowid, total


def fetch_missing_prices(rows, verbose=False):
    """Fetch historical BTC-EUR prices from yfinance for rows missing PRU."""
    dates_needed = set()
    for r in rows:
        if r['pru_eur'] is None or r['pru_eur'] == 0:
            dates_needed.add(r['date'])

    if not dates_needed:
        if verbose:
            print("  No missing prices to fetch.")
        return {}

    print(f"  Fetching BTC-EUR historical prices for {len(dates_needed)} dates...")

    min_date = min(dates_needed)
    max_date = max(dates_needed)
    # Fetch a wider range to ensure we have data for edge dates
    start = (datetime.strptime(min_date, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d')
    end = (datetime.strptime(max_date, '%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d')

    ticker = yf.Ticker(SYMBOL_DB)
    hist = ticker.history(start=start, end=end)

    if hist.empty:
        print(f"  WARNING: No historical data returned for {SYMBOL_DB} ({start} to {end})")
        return {}

    # Build date -> close price map (sorted for fallback to prior date)
    price_by_date = {}
    for idx, row in hist.iterrows():
        date_str = idx.strftime('%Y-%m-%d')
        price_by_date[date_str] = row['Close']

    sorted_dates = sorted(price_by_date.keys())

    # For each needed date, find exact or most recent prior close
    result = {}
    for date in sorted(dates_needed):
        if date in price_by_date:
            result[date] = price_by_date[date]
        else:
            # Find most recent prior date
            prior = [d for d in sorted_dates if d <= date]
            if prior:
                result[date] = price_by_date[prior[-1]]
                if verbose:
                    print(f"    {date}: no exact match, using {prior[-1]} close = {result[date]:.2f}")
            else:
                print(f"  WARNING: No historical price found for {date}")

    if verbose:
        for date in sorted(result):
            print(f"    {date}: {result[date]:.2f} EUR")

    return result


def import_transactions(conn, csv_rows, stockid, base_rowid, missing_prices,
                        dry_run=False, verbose=False):
    """Import CSV rows into the transactions table."""
    inserted = 0
    skipped = 0
    warnings = []

    for csv_row in csv_rows:
        rowid = csv_row['csv_index'] + base_rowid
        txn_type = csv_row['type']
        date = csv_row['date']
        quantity = csv_row['amount_token']

        # Map CSV type to DB type
        if txn_type == 'STACK':
            db_type = 'STAKING'
        elif txn_type == 'BUY':
            db_type = 'BUY'
        else:
            warnings.append(f"WARNING: Unknown transaction type '{txn_type}' at csv_index={csv_row['csv_index']}")
            continue

        # Determine price
        price = csv_row['pru_eur']
        if price is None or price == 0:
            if date in missing_prices:
                price = missing_prices[date]
            else:
                warnings.append(f"WARNING: No price for {date} (csv_index={csv_row['csv_index']})")
                continue

        if verbose:
            amount = quantity * price if db_type == 'BUY' else 0
            print(f"  [{rowid}] {date} {db_type:8s} qty={quantity:.10f} "
                  f"price={price:.2f} amount={amount:.2f}")

        if dry_run:
            inserted += 1
            continue

        cursor = conn.execute(
            "INSERT INTO transactions (stockid, portfolioid, rowid, quantity, price, type, datestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(portfolioid, rowid) DO NOTHING",
            (stockid, PORTFOLIO_ID, rowid, quantity, price, db_type, date)
        )
        if cursor.rowcount > 0:
            inserted += 1
        else:
            skipped += 1

    if not dry_run:
        conn.commit()

    return inserted, skipped, warnings


def update_position(conn, stockid, dry_run=False, verbose=False):
    """Update the position quantity from the sum of all transactions."""
    total_qty = conn.execute(
        "SELECT SUM(quantity) FROM transactions WHERE portfolioid = ? AND stockid = ?",
        (PORTFOLIO_ID, stockid)
    ).fetchone()[0] or 0.0

    if verbose or dry_run:
        print(f"  Total quantity from transactions: {total_qty:.10f}")

    if dry_run:
        print(f"  [DRY-RUN] Would update position quantity to {total_qty:.10f}")
        return

    # Check if position exists
    existing = conn.execute(
        "SELECT quantity FROM positions WHERE stockid = ? AND portfolio_id = ?",
        (stockid, PORTFOLIO_ID)
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE positions SET quantity = ? WHERE stockid = ? AND portfolio_id = ?",
            (total_qty, stockid, PORTFOLIO_ID)
        )
    else:
        conn.execute(
            "INSERT INTO positions (stockid, portfolio_id, quantity) VALUES (?, ?, ?)",
            (stockid, PORTFOLIO_ID, total_qty)
        )

    conn.commit()
    print(f"  Position updated: quantity = {total_qty:.10f}")


def main():
    parser = argparse.ArgumentParser(description='Import crypto transactions from CSV')
    parser.add_argument('csv_file', help='Path to the CSV file')
    parser.add_argument('--dry-run', action='store_true', help='Parse and verify without writing to DB')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print each row being processed')
    parser.add_argument('--db-path', help='Override DB path (default: data/portfolio.db)')
    args = parser.parse_args()

    db_path = get_db_path(args.db_path)
    print(f"DB path: {db_path}")
    print(f"CSV file: {args.csv_file}")
    if args.dry_run:
        print("*** DRY RUN - no changes will be written ***")
    print()

    # Phase 1: Parse CSV
    print("Phase 1: Parsing CSV...")
    csv_rows = parse_csv(args.csv_file)
    type_counts = defaultdict(int)
    for r in csv_rows:
        type_counts[r['type']] += 1
    print(f"  Parsed {len(csv_rows)} rows: {dict(type_counts)}")
    missing_count = sum(1 for r in csv_rows if r['pru_eur'] is None or r['pru_eur'] == 0)
    print(f"  Rows missing prices: {missing_count}")
    print()

    conn = sqlite3.connect(db_path)
    try:
        # Phase 2: Ensure BTC-EUR stock exists
        print("Phase 2: Ensuring BTC-EUR stock exists in DB...")
        stockid = ensure_stock_exists(conn, dry_run=args.dry_run, verbose=args.verbose)
        print()

        # Phase 3: Load existing transactions
        print(f"Phase 3: Loading existing transactions for portfolio {PORTFOLIO_ID}...")
        base_rowid, existing_count = load_existing_transactions(conn, len(csv_rows))
        print(f"  Found {existing_count} existing transactions (base_rowid={base_rowid})")
        print(f"  CSV rows will use rowids {base_rowid}..{base_rowid + len(csv_rows) - 1}")
        print()

        # Phase 4: Fetch missing prices
        print("Phase 4: Fetching historical prices for missing rows...")
        missing_prices = fetch_missing_prices(csv_rows, verbose=args.verbose)
        print()

        # Phase 5: Import transactions
        action = "Simulating import" if args.dry_run else "Importing transactions"
        print(f"Phase 5: {action}...")
        inserted, skipped, warnings = import_transactions(
            conn, csv_rows, stockid, base_rowid, missing_prices,
            dry_run=args.dry_run, verbose=args.verbose
        )
        print()

        # Update position
        print("Updating position...")
        update_position(conn, stockid, dry_run=args.dry_run, verbose=args.verbose)
        print()

        # Summary
        print("=" * 60)
        if args.dry_run:
            print(f"DRY RUN complete: {inserted} rows would be inserted")
        else:
            print(f"Import complete: {inserted} inserted, {skipped} skipped (already existed)")
        if warnings:
            print(f"\n{len(warnings)} warnings:")
            for w in warnings:
                print(f"  {w}")
        else:
            print("No warnings.")

        if not args.dry_run and inserted > 0:
            total = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE portfolioid = ?", (PORTFOLIO_ID,)
            ).fetchone()[0]
            print(f"\nTotal transactions for portfolio {PORTFOLIO_ID}: {total}")
            print("\nRemember to restart the app to refresh position caches:")
            print("  docker compose up --build -d")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
