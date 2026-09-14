#!/usr/bin/env python3
"""7단계 산출물 존재 여부와 요구사항 추적의 기본 무결성을 검사한다."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

EXPECTED = [
    "00_개발계획.md", "01_SRS.md", "02_PRD_FS.md", "03_IA.md",
    "04_와이어프레임명세.md", "05_UI디자인명세.md", "06_구현기록.md", "07_테스트결과.md",
]
REQ_PATTERN = re.compile(r"\b(?:FR|NFR|SEC|DATA)-\d{3}\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="개발 문서 추적성 검사")
    parser.add_argument("--docs", required=True, type=Path, help="7단계 문서 폴더")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    missing_files = [name for name in EXPECTED if not (args.docs / name).is_file()]
    if missing_files:
        print("missing files:", ", ".join(missing_files))
        return 1

    srs = (args.docs / "01_SRS.md").read_text(encoding="utf-8")
    prd = (args.docs / "02_PRD_FS.md").read_text(encoding="utf-8")
    tests = (args.docs / "07_테스트결과.md").read_text(encoding="utf-8")
    requirements = set(REQ_PATTERN.findall(srs))
    if not requirements:
        print("SRS에 요구사항 ID가 없습니다.")
        return 1

    missing_prd = sorted(req for req in requirements if req not in prd)
    missing_tests = sorted(req for req in requirements if req not in tests)
    if missing_prd or missing_tests:
        if missing_prd:
            print("PRD/FS 추적 누락:", ", ".join(missing_prd))
        if missing_tests:
            print("테스트 추적 누락:", ", ".join(missing_tests))
        return 1

    print(f"OK: {len(EXPECTED)}개 문서, {len(requirements)}개 요구사항 추적 확인")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
