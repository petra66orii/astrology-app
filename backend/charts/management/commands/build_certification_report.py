from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from charts.certification import build_certification_report


class Command(BaseCommand):
    help = "Build a machine-readable Gate B comparison report from golden fixtures."

    def add_arguments(self, parser):
        parser.add_argument("fixtures", type=Path)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--markdown-output", type=Path)

    def handle(self, *args, **options):
        source: Path = options["fixtures"]
        output: Path = options["output"]
        report = build_certification_report(json.loads(source.read_text(encoding="utf-8")))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        markdown_output: Path | None = options.get("markdown_output")
        if markdown_output:
            lines = [
                "# Gate B calculation-correctness report",
                "",
                f"Decision: **{report['gate_decision']}**",
                "",
                f"Fixtures: {report['summary']['PASS']} passed, {report['summary']['FAIL']} failed, {report['summary']['BLOCKED']} blocked.",
                "",
                "Provider values are intentionally blank until a credentialed, budget-guarded live run is approved.",
            ]
            for fixture in report["fixtures"]:
                lines.extend(
                    [
                        "",
                        f"## {fixture['fixture_id']} — {fixture['status']}",
                        "",
                        "| Value | Prokerala | Independent reference | Absolute difference | Tolerance | Result |",
                        "|---|---:|---:|---:|---:|---|",
                    ]
                )
                for item in fixture["comparisons"]:
                    result = (
                        "BLOCKED"
                        if item["passed"] is None
                        else "PASS"
                        if item["passed"]
                        else "FAIL"
                    )
                    lines.append(
                        f"| {item['field']} | {item['provider']} | {item['reference']} | {item['difference']} | {item['tolerance']} | {result} |"
                    )
            markdown_output.parent.mkdir(parents=True, exist_ok=True)
            markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.stdout.write(f"Gate B decision: {report['gate_decision']}")
