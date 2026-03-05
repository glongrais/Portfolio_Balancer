#!/usr/bin/env python3
"""
One-time import script for CTO portfolio (portfolio_id=3, USD) transactions
from a broker-exported CSV file.

Usage:
    cd stock_portfolio_app
    ../.venv/bin/python scripts/import_cto_csv.py ../Transactions-CTO.csv
    ../.venv/bin/python scripts/import_cto_csv.py ../Transactions-CTO.csv --dry-run --verbose
"""

import argparse
import csv
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

import yfinance as yf

PORTFOLIO_ID = 3
WITHHOLDING_TAX_RATE = 0.85  # 15% withholding tax on dividends
LOGO_URL_TEMPLATE = "https://api.elbstream.com/logos/symbol/{symbol}?format=png&size=128"


def get_db_path(override=None):
    if override:
        return override
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.environ.get('PORTFOLIO_DB_PATH', os.path.join(project_root, 'data', 'portfolio.db'))


def parse_number(s):
    """Strip ' US$' suffix and convert European decimal format to float."""
    s = s.strip()
    if not s:
        return None
    s = s.replace('\xa0US$', '').replace(' US$', '').replace(',', '.')
    return float(s)


def parse_csv(filepath):
    """Parse the broker CSV into a list of dicts."""
    rows = []
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader)
        assert header == ['Date', 'Type', 'Symbol', 'Name', 'Quantity', 'Price', 'Amount'], \
            f"Unexpected CSV header: {header}"

        for i, row in enumerate(reader):
            date_str, txn_type, symbol, name, qty_str, price_str, amount_str = row
            date = date_str.replace('/', '-')
            quantity = parse_number(qty_str)
            price = parse_number(price_str)
            amount = parse_number(amount_str)

            rows.append({
                'csv_index': i,
                'date': date,
                'type': txn_type,
                'symbol': symbol,
                'name': name,
                'quantity': quantity,
                'price': price,
                'amount': amount,
            })

    return rows


def ensure_stocks_exist(conn, symbols, dry_run=False, verbose=False):
    """Ensure all symbols exist in the stocks table. Returns symbol->stockid map."""
    symbol_to_stockid = {}

    for symbol in sorted(symbols):
        row = conn.execute("SELECT stockid FROM stocks WHERE symbol = ?", (symbol,)).fetchone()
        if row:
            symbol_to_stockid[symbol] = row[0]
            if verbose:
                print(f"  Stock {symbol} already exists (stockid={row[0]})")
        else:
            if dry_run:
                print(f"  [DRY-RUN] Would insert stock {symbol} (fetching metadata from yfinance)")
                info = yf.Ticker(symbol).info
                print(f"    -> {info.get('longName', '?')}, currency={info.get('currency', '?')}")
                symbol_to_stockid[symbol] = -1  # placeholder
            else:
                print(f"  Inserting stock {symbol}...")
                info = yf.Ticker(symbol).info

                ex_div_raw = info.get("exDividendDate")
                ex_dividend_date = None
                if ex_div_raw is not None:
                    if isinstance(ex_div_raw, (int, float)):
                        try:
                            ex_dividend_date = datetime.fromtimestamp(ex_div_raw).strftime('%Y-%m-%d')
                        except (ValueError, TypeError, OSError):
                            pass
                    elif hasattr(ex_div_raw, 'strftime'):
                        ex_dividend_date = ex_div_raw.strftime('%Y-%m-%d')
                    elif isinstance(ex_div_raw, str):
                        ex_dividend_date = ex_div_raw

                conn.execute('''
                    INSERT INTO stocks (symbol, name, price, currency, market_cap, sector, industry, country, logo_url, quote_type, ex_dividend_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        name=excluded.name, price=excluded.price, currency=excluded.currency,
                        market_cap=excluded.market_cap, sector=excluded.sector, industry=excluded.industry,
                        country=excluded.country, logo_url=excluded.logo_url, quote_type=excluded.quote_type,
                        ex_dividend_date=excluded.ex_dividend_date
                ''', (
                    symbol,
                    info.get("longName", ""),
                    info.get("currentPrice", info.get("previousClose")),
                    info.get("currency", ""),
                    info.get("marketCap"),
                    info.get("sector", ""),
                    info.get("industry", ""),
                    info.get("country", ""),
                    LOGO_URL_TEMPLATE.format(symbol=symbol),
                    info.get("quoteType", "EQUITY"),
                    ex_dividend_date,
                ))
                conn.commit()

                row = conn.execute("SELECT stockid FROM stocks WHERE symbol = ?", (symbol,)).fetchone()
                symbol_to_stockid[symbol] = row[0]
                print(f"    -> stockid={row[0]}, name={info.get('longName', '?')}")

    return symbol_to_stockid


def load_existing_transactions(conn, csv_row_count):
    """Load pre-import transactions, compute deterministic base_rowid, and build seed quantities.

    For idempotency, base_rowid must be the same across runs. We detect whether
    CSV rows were already imported by comparing total transaction count to the
    CSV size: pre_existing_count = total - csv_row_count (if CSV was imported)
    or total (if not yet imported).  Only pre-existing transactions seed the
    accumulated quantity tracker.
    """
    total = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE portfolioid = ?", (PORTFOLIO_ID,)
    ).fetchone()[0]

    max_rowid = conn.execute(
        "SELECT COALESCE(MAX(rowid), -1) FROM transactions WHERE portfolioid = ?", (PORTFOLIO_ID,)
    ).fetchone()[0]

    if total > csv_row_count:
        # CSV was already imported; pre-existing rows are the remainder
        pre_existing_count = total - csv_row_count
        base_rowid = pre_existing_count
    else:
        # First import
        pre_existing_count = total
        base_rowid = max_rowid + 1

    # Build stockid -> symbol reverse map
    stockid_to_symbol = {}
    for row in conn.execute("SELECT stockid, symbol FROM stocks").fetchall():
        stockid_to_symbol[row[0]] = row[1]

    # Seed accumulated quantities from pre-existing transactions only
    pre_existing_rows = conn.execute(
        "SELECT rowid, stockid, type, quantity FROM transactions "
        "WHERE portfolioid = ? AND rowid < ? ORDER BY datestamp, rowid",
        (PORTFOLIO_ID, base_rowid)
    ).fetchall()

    accumulated_qty = defaultdict(float)
    for rowid, stockid, txn_type, quantity in pre_existing_rows:
        symbol = stockid_to_symbol.get(stockid, f"?stockid={stockid}")
        if txn_type == 'BUY':
            accumulated_qty[symbol] += quantity
        elif txn_type == 'SELL':
            accumulated_qty[symbol] -= quantity

    return accumulated_qty, base_rowid, total


def fetch_dividend_history(symbols, verbose=False):
    """Fetch historical dividend data from yfinance for given symbols."""
    div_history = {}
    for symbol in sorted(symbols):
        if verbose:
            print(f"  Fetching dividend history for {symbol}...")
        raw = yf.Ticker(symbol).get_dividends()
        div_history[symbol] = {t.strftime('%Y-%m-%d'): v for t, v in raw.to_dict().items()}
        if verbose:
            print(f"    -> {len(div_history[symbol])} ex-dividend dates found")
    return div_history


def resolve_dividend(csv_row, accumulated_qty, div_history, verbose=False):
    """
    Resolve a DIVIDEND row: find the matching ex-date and compute quantity/price.
    Returns (quantity, price, warning_msg or None).
    """
    symbol = csv_row['symbol']
    csv_amount = csv_row['amount']
    payment_date = csv_row['date']
    qty = accumulated_qty.get(symbol, 0.0)

    if qty <= 0:
        return qty, csv_amount, f"WARNING: No shares held for {symbol} on {payment_date} but got dividend {csv_amount}"

    symbol_divs = div_history.get(symbol, {})
    if not symbol_divs:
        # No dividend history available - use fallback
        price = csv_amount / qty
        return qty, price, f"WARNING: No dividend history for {symbol}, using fallback price={price:.6f}"

    # Find the latest ex-date that is 1-60 days before payment date
    payment_dt = datetime.strptime(payment_date, '%Y-%m-%d')
    best_ex_date = None
    best_gross_dps = None
    best_delta = None

    for ex_date_str, gross_dps in symbol_divs.items():
        ex_dt = datetime.strptime(ex_date_str, '%Y-%m-%d')
        delta = (payment_dt - ex_dt).days
        if 1 <= delta <= 60:
            if best_delta is None or delta < best_delta:
                best_ex_date = ex_date_str
                best_gross_dps = gross_dps
                best_delta = delta

    if best_gross_dps is None:
        price = csv_amount / qty
        return qty, price, (
            f"WARNING: No matching ex-date for {symbol} dividend on {payment_date} "
            f"(csv_amount={csv_amount:.2f}), using fallback price={price:.6f}"
        )

    after_tax_dps = best_gross_dps * WITHHOLDING_TAX_RATE
    expected_amount = qty * after_tax_dps
    tolerance = max(0.02, csv_amount * 0.10)

    if abs(expected_amount - csv_amount) <= tolerance:
        if verbose:
            print(f"    Matched ex-date {best_ex_date} (delta={best_delta}d): "
                  f"gross_dps={best_gross_dps:.4f}, after_tax={after_tax_dps:.4f}, "
                  f"expected={expected_amount:.4f}, csv={csv_amount:.2f}")
        return qty, after_tax_dps, None
    else:
        fallback_price = csv_amount / qty
        return qty, fallback_price, (
            f"WARNING: Amount mismatch for {symbol} on {payment_date}: "
            f"ex-date={best_ex_date}, expected={expected_amount:.4f} vs csv={csv_amount:.2f} "
            f"(diff={abs(expected_amount - csv_amount):.4f}, tol={tolerance:.4f}), "
            f"using fallback price={fallback_price:.6f}"
        )


def import_transactions(conn, csv_rows, symbol_to_stockid, accumulated_qty, base_rowid,
                        div_history, dry_run=False, verbose=False):
    """Import CSV rows into the transactions table."""
    inserted = 0
    skipped = 0
    warnings = []

    for csv_row in csv_rows:
        rowid = csv_row['csv_index'] + base_rowid
        symbol = csv_row['symbol']
        txn_type = csv_row['type']
        date = csv_row['date']
        stockid = symbol_to_stockid.get(symbol)

        if txn_type in ('BUY', 'SELL'):
            quantity = csv_row['quantity']
            price = csv_row['price']

            # Update accumulated position tracker
            if txn_type == 'BUY':
                accumulated_qty[symbol] = accumulated_qty.get(symbol, 0.0) + quantity
            else:
                accumulated_qty[symbol] = accumulated_qty.get(symbol, 0.0) - quantity

            if verbose:
                print(f"  [{rowid}] {date} {txn_type:8s} {symbol:8s} qty={quantity:.6f} "
                      f"price={price:.2f} (held={accumulated_qty.get(symbol, 0):.6f})")

        elif txn_type == 'DIVIDEND':
            quantity, price, warning = resolve_dividend(csv_row, accumulated_qty, div_history, verbose)
            if warning:
                warnings.append(warning)
                if verbose:
                    print(f"  [{rowid}] {date} DIVIDEND  {symbol:8s} {warning}")
            elif verbose:
                print(f"  [{rowid}] {date} DIVIDEND  {symbol:8s} qty={quantity:.6f} "
                      f"price={price:.6f} amount={csv_row['amount']:.2f}")

        else:
            warnings.append(f"WARNING: Unknown transaction type '{txn_type}' at csv_index={csv_row['csv_index']}")
            continue

        if dry_run:
            inserted += 1  # count what would be inserted
            continue

        cursor = conn.execute(
            "INSERT INTO transactions (stockid, portfolioid, rowid, quantity, price, type, datestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(portfolioid, rowid) DO NOTHING",
            (stockid, PORTFOLIO_ID, rowid, quantity, price, txn_type, date)
        )
        if cursor.rowcount > 0:
            inserted += 1
        else:
            skipped += 1

    if not dry_run:
        conn.commit()

    return inserted, skipped, warnings


def main():
    parser = argparse.ArgumentParser(description='Import CTO portfolio transactions from broker CSV')
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
    symbols = sorted(set(r['symbol'] for r in csv_rows))
    print(f"  Symbols: {', '.join(symbols)}")
    print()

    conn = sqlite3.connect(db_path)
    try:
        # Phase 2: Ensure stocks exist
        print("Phase 2: Ensuring all stocks exist in DB...")
        symbol_to_stockid = ensure_stocks_exist(conn, symbols, dry_run=args.dry_run, verbose=args.verbose)
        print()

        # Phase 3: Load existing transactions
        print("Phase 3: Loading existing transactions for portfolio 3...")
        accumulated_qty, base_rowid, existing_count = load_existing_transactions(conn, len(csv_rows))
        print(f"  Found {existing_count} existing transactions (base_rowid={base_rowid})")
        print(f"  Starting quantities: {dict(accumulated_qty)}")
        print(f"  CSV rows will use rowids {base_rowid}..{base_rowid + len(csv_rows) - 1}")
        print()

        # Phase 4: Fetch dividend history
        dividend_symbols = sorted(set(r['symbol'] for r in csv_rows if r['type'] == 'DIVIDEND'))
        print(f"Phase 4: Fetching dividend history for {len(dividend_symbols)} symbols...")
        div_history = fetch_dividend_history(dividend_symbols, verbose=args.verbose)
        print()

        # Phase 5: Import transactions
        action = "Simulating import" if args.dry_run else "Importing transactions"
        print(f"Phase 5: {action}...")
        inserted, skipped, warnings = import_transactions(
            conn, csv_rows, symbol_to_stockid, accumulated_qty, base_rowid,
            div_history, dry_run=args.dry_run, verbose=args.verbose
        )
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
            print(f"\nTotal transactions for portfolio 3: {total}")
            print("\nRemember to restart the app to refresh position caches:")
            print("  docker compose up --build -d")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
