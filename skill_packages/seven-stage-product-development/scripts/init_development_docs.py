#!/usr/bin/env python3
"""7단계 개발 문서 템플릿을 새 프로젝트 폴더에 안전하게 복사한다."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="7단계 개발 문서 골격 생성")
    parser.add_argument("--project", required=True, help="문서에 표시할 프로젝트명")
    parser.add_argument("--output", required=True, type=Path, help="생성할 문서 폴더")
    parser.add_argument("--owner", default="미정", help="프로젝트 책임자 또는 팀")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    template_dir = Path(__file__).resolve().parents[1] / "assets" / "templates"
    templates = sorted(template_dir.glob("*.template.md"))
    if not templates:
        raise SystemExit("템플릿을 찾지 못했습니다.")

    args.output.mkdir(parents=True, exist_ok=True)
    targets = [(source, args.output / source.name.replace(".template", "")) for source in templates]
    conflicts = [target for _, target in targets if target.exists()]
    if conflicts:
        names = ", ".join(path.name for path in conflicts)
        raise SystemExit(f"기존 파일을 덮어쓰지 않습니다: {names}")

    replacements = {
        "{{PROJECT_NAME}}": args.project,
        "{{DATE}}": date.today().isoformat(),
        "{{OWNER}}": args.owner,
    }
    for source, target in targets:
        content = source.read_text(encoding="utf-8")
        for key, value in replacements.items():
            content = content.replace(key, value)
        target.write_text(content, encoding="utf-8")
        print(f"created {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
