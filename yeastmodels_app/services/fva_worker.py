"""Subprocess entry point for running FVA without risking the UI process."""

from __future__ import annotations

import argparse
import json
import sys

from yeastmodels_app.services.model_service import YeastModelService


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["batch", "single"], default="batch")
    parser.add_argument("--condition-id", default="default")
    parser.add_argument("--scope", default="open_exchange")
    parser.add_argument("--reaction-id", default="")
    parser.add_argument("--fraction-of-optimum", type=float, default=0.95)
    args = parser.parse_args()

    service = YeastModelService()
    if args.mode == "single":
        if not args.reaction_id:
            raise ValueError("--reaction-id is required in single mode.")
        payload = service.run_single_reaction_fva(
            condition_id=args.condition_id,
            reaction_id=args.reaction_id,
            fraction_of_optimum=args.fraction_of_optimum,
        )
    else:
        result = service.run_fva(
            condition_id=args.condition_id,
            scope=args.scope,
            fraction_of_optimum=args.fraction_of_optimum,
        )
        payload = result.to_dict()

    print("FVA_JSON:" + json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
