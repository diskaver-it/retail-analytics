"""CLI for the EL half of the pipeline: python -m retail_analytics [command]."""
from __future__ import annotations

import argparse
from pathlib import Path

from . import config, ingest, synthetic, warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="retail_analytics")
    parser.add_argument("command", nargs="?", default="all",
                        choices=["ingest", "load", "all", "synthetic"])
    parser.add_argument("--force", action="store_true",
                        help="re-download and re-parse instead of reusing what is on disk")
    parser.add_argument("--warehouse", type=Path, default=config.WAREHOUSE,
                        help="DuckDB file to write to")
    args = parser.parse_args(argv)

    if args.command == "synthetic":
        rows = synthetic.build_warehouse(args.warehouse)
        print(f"seeded  {warehouse.RAW_TABLE}  {rows:,} synthetic rows -> {args.warehouse}")
        return 0

    if args.command in ("ingest", "all"):
        for path in ingest.run(force_download=args.force):
            print(f"landed  {path.name}  {path.stat().st_size / 1e6:.1f} MB")

    if args.command in ("load", "all"):
        rows = warehouse.load_raw(warehouse=args.warehouse)
        print(f"loaded  {warehouse.RAW_TABLE}  {rows:,} rows")
        for key, value in warehouse.profile(warehouse=args.warehouse).items():
            print(f"  {key:<24} {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
