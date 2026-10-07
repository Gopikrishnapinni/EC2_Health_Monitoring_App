from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from .monitor import EC2HealthMonitor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check AWS EC2 instance and system health.",
    )
    parser.add_argument("--region", help="AWS region; defaults to AWS configuration.")
    parser.add_argument(
        "--instance-id",
        action="append",
        dest="instance_ids",
        help="Instance ID to check. Repeat for multiple IDs; default checks all visible instances.",
    )
    parser.add_argument(
        "--cpu-threshold",
        type=float,
        help="Mark instances unhealthy when recent average CPU exceeds this percentage.",
    )
    parser.add_argument("--lookback-minutes", type=int, default=15)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _print_table(results: list[dict[str, object]]) -> None:
    headers = ["ID", "Name", "State", "Instance", "System", "CPU", "Health", "Reason"]
    rows = [
        [
            str(item["instance_id"]),
            str(item["name"]),
            str(item["state"]),
            str(item["instance_status"]),
            str(item["system_status"]),
            "-" if item["cpu_utilization"] is None else f'{item["cpu_utilization"]:.1f}%',
            "HEALTHY" if item["healthy"] else "UNHEALTHY",
            str(item["reason"]),
        ]
        for item in results
    ]
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    print("  ".join(header.ljust(widths[i]) for i, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.lookback_minutes <= 0:
        print("--lookback-minutes must be greater than zero.", file=sys.stderr)
        return 2
    if args.cpu_threshold is not None and not 0 <= args.cpu_threshold <= 100:
        print("--cpu-threshold must be between 0 and 100.", file=sys.stderr)
        return 2

    try:
        session = boto3.Session(region_name=args.region)
        monitor = EC2HealthMonitor(
            session.client("ec2"),
            session.client("cloudwatch") if args.cpu_threshold is not None else None,
        )
        results = [
            result.to_dict()
            for result in monitor.collect(
                instance_ids=args.instance_ids,
                cpu_threshold=args.cpu_threshold,
                lookback_minutes=args.lookback_minutes,
            )
        ]
    except (BotoCoreError, ClientError, NoCredentialsError) as exc:
        print(f"AWS monitoring failed: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(results, indent=2))
    else:
        _print_table(results)
    return 0 if all(item["healthy"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

