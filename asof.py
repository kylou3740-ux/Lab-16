"""
FIN 43900 — Lab 16: Provenance Gate

Run:
    python asof.py

Uses only the Python standard library. Edit DECISION_DATE and DATA to test
different decision dates or input tables.
"""

from collections import defaultdict
from datetime import date

DECISION_DATE = date.fromisoformat("2026-03-31")

# row, ticker, month measured, publication date, index value
DATA = [
    (1, "AAA", "2026-01", "2026-02-10", 101.0),
    (2, "AAA", "2026-02", "2026-03-10", 104.0),
    (3, "AAA", "2026-03", "2026-04-10", 109.0),
    (4, "AAA", "2026-02", "2026-03-25", 103.0),
    (5, "BBB", "2026-01", "2026-02-10", 98.0),
    (6, "BBB", "2026-02", "2026-03-10", 97.0),
    (7, "BBB", "2026-02", "2026-03-10", 97.0),
    (8, "BBB", "2026-03", "2026-04-10", 92.0),
    (9, "CCC", "2026-01", "2026-02-10", 110.0),
    (10, "CCC", "2026-02", "2026-04-05", 112.0),
    (11, "", "2026-02", "2026-03-10", 99.0),
    (12, "CCC", "2026-02", "2026-03-10", 111.0),
]


def parse_row(row):
    """Convert publication date to a date while preserving the row number."""
    row_number, ticker, month, published_on, index_value = row
    return {
        "row": row_number,
        "ticker": ticker.strip(),
        "month": month,
        "published": date.fromisoformat(published_on),
        "index": float(index_value),
    }


def describe_removed(rows):
    return ", ".join(str(row["row"]) for row in rows) if rows else "none"


def exact_duplicate_key(row):
    """Duplicate means all data fields match; row number is only an identifier."""
    return (row["ticker"], row["month"], row["published"], row["index"])


def remove_exact_duplicates(rows):
    seen = set()
    kept = []
    removed = []
    for row in rows:
        key = exact_duplicate_key(row)
        if key in seen:
            removed.append(row)
        else:
            seen.add(key)
            kept.append(row)
    return kept, removed


def keep_latest_revision(rows):
    """For each ticker/month, keep the latest publication; break ties by row."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["ticker"], row["month"])].append(row)

    kept = []
    removed = []
    for group in grouped.values():
        group.sort(key=lambda row: (row["published"], row["row"]))
        kept.append(group[-1])
        removed.extend(group[:-1])

    kept.sort(key=lambda row: row["row"])
    removed.sort(key=lambda row: row["row"])
    return kept, removed


def signal_for_ticker(rows):
    """Return latest-month percent change versus the previous month, if available."""
    by_month = {row["month"]: row for row in rows}
    months = sorted(by_month)
    if len(months) < 2:
        return None

    previous_month, latest_month = months[-2], months[-1]
    previous_value = by_month[previous_month]["index"]
    latest_value = by_month[latest_month]["index"]
    if previous_value == 0:
        return latest_month, None, previous_month
    change = (latest_value / previous_value - 1) * 100
    return latest_month, change, previous_month


def print_panel(title, rows):
    print(f"\n{title}")
    print(f"{'Row':>3}  {'Ticker':<6} {'Month':<8} {'Published':<12} {'Index':>7}")
    print("-" * 43)
    for row in sorted(rows, key=lambda item: (item["ticker"], item["month"], item["row"])):
        print(
            f"{row['row']:>3}  {row['ticker']:<6} {row['month']:<8} "
            f"{row['published'].isoformat():<12} {row['index']:>7.1f}"
        )


def print_signals(title, rows):
    print(f"\n{title}")
    tickers = sorted({row["ticker"] for row in rows})
    for ticker in tickers:
        ticker_rows = [row for row in rows if row["ticker"] == ticker]
        result = signal_for_ticker(ticker_rows)
        if result is None:
            print(f"{ticker}: not enough monthly observations")
            continue
        latest_month, change, previous_month = result
        if change is None:
            print(f"{ticker}: cannot calculate; previous-month index is zero")
        else:
            print(
                f"{ticker}: {change:+.2f}% ({latest_month}; "
                f"{previous_month} to {latest_month})"
            )


def main():
    rows = [parse_row(row) for row in DATA]
    print("FIN 43900 LAB 16 — PROVENANCE GATE")
    print(f"Decision date: {DECISION_DATE.isoformat()}")
    print(f"Input rows: {len(rows)}")

    # Rule 1: quarantine rows with no ticker.
    quarantined = [row for row in rows if not row["ticker"]]
    remaining = [row for row in rows if row["ticker"]]
    print(f"\nRule 1 — quarantine rows with no ticker: removed {len(quarantined)} row(s): "
          f"{describe_removed(quarantined)}")

    # Rule 2: remove exact duplicates.
    remaining, duplicates = remove_exact_duplicates(remaining)
    print(f"Rule 2 — remove exact duplicates: removed {len(duplicates)} row(s): "
          f"{describe_removed(duplicates)}")

    # Preserve this cleaned dataset for the naive comparison. The naive version
    # ignores publication timing but still resolves duplicate rows and revisions.
    cleaned_for_naive = list(remaining)

    # Rule 3: remove rows published after the decision date.
    future_rows = [row for row in remaining if row["published"] > DECISION_DATE]
    remaining = [row for row in remaining if row["published"] <= DECISION_DATE]
    print(f"Rule 3 — published after {DECISION_DATE.isoformat()}: "
          f"removed {len(future_rows)} row(s): {describe_removed(future_rows)}")

    # Rule 4: among rows available by the decision date, keep the latest revision
    # for each ticker/month.
    remaining, revisions = keep_latest_revision(remaining)
    print(f"Rule 4 — older vintage replaced by a revision: removed {len(revisions)} row(s): "
          f"{describe_removed(revisions)}")

    print_panel("AS-OF PANEL (information available on the decision date)", remaining)
    print_signals("AS-OF SIGNALS", remaining)

    # Naive comparison: do not filter on publication date. Select the latest
    # publication for each ticker/month, including publications after the
    # decision date, then calculate the latest-month change.
    naive_panel, naive_revisions = keep_latest_revision(cleaned_for_naive)
    print_panel("NAIVE PANEL (ignores publication date; includes later information)", naive_panel)
    print_signals("NAIVE SIGNALS", naive_panel)

    print("\nInterpretation:")
    print("The as-of panel uses only records published on or before the decision date.")
    print("The naive panel can use later releases or revisions, creating look-ahead bias.")


if __name__ == "__main__":
    main()
