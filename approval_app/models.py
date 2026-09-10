from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PageSnapshot:
    page: int
    text: str
    normalized_text: str
    word_count: int


@dataclass
class FieldValue:
    key: str
    value: str
    page: int
    section: str
    evidence: str


@dataclass
class DocumentSnapshot:
    filename: str
    sha256: str
    page_count: int
    metadata: dict[str, str]
    pages: list[PageSnapshot]
    fields: list[FieldValue]
    extraction_quality: str
    raw_bytes: bytes = field(repr=False)


@dataclass
class Change:
    category: str
    section: str
    old_page: int | None
    new_page: int | None
    item: str
    old_value: str
    new_value: str
    change_type: str
    issue_type: str = ""
    severity: str = "정보"
    confidence: str = "높음"
    evidence: str = ""
    guide: str = ""
    review_status: str = "보류"
    review_comment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Issue:
    category: str
    section: str
    page: int
    item: str
    issue_type: str
    severity: str
    confidence: str
    evidence: str
    guide: str
    review_status: str = "보류"
    review_comment: str = ""

    def to_change(self) -> Change:
        return Change(
            category=self.category,
            section=self.section,
            old_page=None,
            new_page=self.page,
            item=self.item,
            old_value="",
            new_value=self.evidence,
            change_type="검토 필요",
            issue_type=self.issue_type,
            severity=self.severity,
            confidence=self.confidence,
            evidence=self.evidence,
            guide=self.guide,
            review_status=self.review_status,
            review_comment=self.review_comment,
        )


@dataclass
class PageComparison:
    old_page: int | None
    new_page: int | None
    text_similarity: float
    visual_difference: float
    status: str


@dataclass
class ComparisonResult:
    old_document: DocumentSnapshot
    new_document: DocumentSnapshot
    changes: list[Change]
    issues: list[Issue]
    pages: list[PageComparison]

    @property
    def review_rows(self) -> list[Change]:
        return self.changes + [issue.to_change() for issue in self.issues]

