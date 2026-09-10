from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from difflib import SequenceMatcher

import pdfplumber
import pypdfium2 as pdfium
from PIL import ImageChops
from pypdf import PdfReader

from .models import (
    Change,
    ComparisonResult,
    DocumentSnapshot,
    FieldValue,
    Issue,
    PageComparison,
    PageSnapshot,
)

APP_VERSION = "1.0.0"
VISUAL_CHANGE_THRESHOLD = 0.03

SPEC_KEYS = [
    "전원용량(전압/전류)", "부팅 시간(개발 모드 기준)", "Silverlight for Windows Embedded",
    ".NET Compact Framework 3.5", "Windows Mobile Device Center", "Remote Desktop Connection",
    "Office 2007 PowerPoint Viewer", "Office 2007 Excel Viewer", "Office 2007 Word Viewer",
    "Internet Explorer 6.0", "USB Flash Driver", "SmartX Framework", "프로그램 메모리",
    "BacklightOn/Off", "AD Converter", "SD Memory", "USB Device", "USB Host", "제품무게",
    "동작온도", "보관온도", "Luminance", "Backlight", "System Touch", "Ethernet", "WLAN",
    "RS232", "RS485", "Audio", "Cache", "Flash", "GPIO", "PWM", "Color", "Size", "RAM",
    "RTC", "TTL", "IIC", "CPU", "전원", "O/S 언어",
]

TYPO_RULES = {
    "Optimun": ("오타", "경고", "Optimum으로 수정할지 원본 제품 명칭과 대조하십시오."),
    "Moblie": ("오타", "경고", "Mobile로 수정하십시오."),
    "Ghz": ("표기 불일치", "주의", "SI 표기인 GHz로 통일하십시오."),
    "콘넥터": ("표기 불일치", "정보", "조직 표준 용어가 없다면 '커넥터'로 통일하십시오."),
}


class PdfValidationError(ValueError):
    pass


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def comparable(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or "")).casefold()


def section_for_page(text: str, page: int) -> str:
    for line in text.splitlines():
        match = re.match(r"\s*(\d+)\.\s*(.+)", line)
        if match:
            return normalize_text(match.group(2))
    return "표지" if page == 1 else f"{page}페이지"


def _extract_fields(pages: list[PageSnapshot]) -> list[FieldValue]:
    fields: list[FieldValue] = []
    seen: set[tuple[str, int]] = set()
    for page in pages:
        section = section_for_page(page.text, page.page)
        lines = [normalize_text(line) for line in page.text.splitlines() if normalize_text(line)]
        joined = "\n".join(lines)
        patterns = [
            ("등록번호", r"등록번호\s*:\s*([^\n]+)"),
            ("발행일자", r"발행일자\s*:\s*([^\n]+)"),
        ]
        if page.page == 1:
            patterns.insert(0, ("모델번호", r"Model\s+No\.?\s*:?\s*(IEC[A-Z0-9-]+)"))
        if "하드웨어 사양" in joined:
            patterns.append(("하드웨어 사양 모델번호", r"Model\s+no\s*:\s*(IEC[A-Z0-9-]+)"))
        for key, pattern in patterns:
            match = re.search(pattern, joined, flags=re.IGNORECASE)
            if match and (key, page.page) not in seen:
                value = normalize_text(match.group(1))
                fields.append(FieldValue(key, value, page.page, section, match.group(0)))
                seen.add((key, page.page))

        for line in lines:
            for key in SPEC_KEYS:
                if line == key or not line.startswith(key):
                    continue
                value = normalize_text(re.sub(r"^\s*:?\s*", "", line[len(key):]))
                if value and (key, page.page) not in seen:
                    fields.append(FieldValue(key, value, page.page, section, line))
                    seen.add((key, page.page))
                break
    return fields


def extract_document(pdf_data: bytes, filename: str) -> DocumentSnapshot:
    if not filename.lower().endswith(".pdf"):
        raise PdfValidationError("PDF 파일만 입력할 수 있습니다.")
    if not pdf_data:
        raise PdfValidationError("빈 파일입니다.")

    try:
        reader = PdfReader(io.BytesIO(pdf_data))
        if reader.is_encrypted:
            raise PdfValidationError("암호화된 PDF는 v1에서 지원하지 않습니다.")
        page_count = len(reader.pages)
    except PdfValidationError:
        raise
    except Exception as exc:
        raise PdfValidationError("PDF 구조를 읽을 수 없습니다.") from exc

    pages: list[PageSnapshot] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                pages.append(PageSnapshot(
                    page=page_no,
                    text=text,
                    normalized_text=normalize_text(text),
                    word_count=len(page.extract_words()),
                ))
    except Exception as exc:
        raise PdfValidationError("PDF 텍스트를 추출하지 못했습니다.") from exc

    text_pages = sum(bool(page.normalized_text) for page in pages)
    quality = "확정" if text_pages == page_count else "검토 필요"
    metadata = {str(k).lstrip("/"): str(v) for k, v in (reader.metadata or {}).items() if v is not None}
    return DocumentSnapshot(
        filename=filename,
        sha256=hashlib.sha256(pdf_data).hexdigest(),
        page_count=page_count,
        metadata=metadata,
        pages=pages,
        fields=_extract_fields(pages),
        extraction_quality=quality,
        raw_bytes=pdf_data,
    )


def render_page(pdf_data: bytes, page_no: int, scale: float = 1.5):
    document = pdfium.PdfDocument(pdf_data)
    if page_no < 1 or page_no > len(document):
        document.close()
        raise IndexError("페이지 범위를 벗어났습니다.")
    page = document[page_no - 1]
    try:
        image = page.render(scale=scale).to_pil().convert("RGB")
        return image.copy()
    finally:
        page.close()
        document.close()


def visual_difference(old_data: bytes, new_data: bytes, old_page: int, new_page: int) -> float:
    old_image = render_page(old_data, old_page, scale=1.0).convert("L")
    new_image = render_page(new_data, new_page, scale=1.0).convert("L")
    if old_image.size != new_image.size:
        new_image = new_image.resize(old_image.size)
    diff = ImageChops.difference(old_image, new_image)
    histogram = diff.histogram()
    changed = sum(histogram[9:])
    return changed / (old_image.width * old_image.height)


def _field_map(document: DocumentSnapshot) -> dict[str, FieldValue]:
    result: dict[str, FieldValue] = {}
    for field in document.fields:
        result[field.key] = field
    return result


def _compare_fields(old: DocumentSnapshot, new: DocumentSnapshot) -> list[Change]:
    old_fields = _field_map(old)
    new_fields = _field_map(new)
    changes: list[Change] = []
    for key in dict.fromkeys([*old_fields, *new_fields]):
        before, after = old_fields.get(key), new_fields.get(key)
        if before and after and comparable(before.value) == comparable(after.value):
            continue
        if before is None:
            change_type = "추가"
        elif after is None:
            change_type = "삭제"
        else:
            change_type = "수정"
        changes.append(Change(
            category="사양/식별정보",
            section=(after or before).section,
            old_page=before.page if before else None,
            new_page=after.page if after else None,
            item=key,
            old_value=before.value if before else "-",
            new_value=after.value if after else "-",
            change_type=change_type,
            evidence=" / ".join(x.evidence for x in (before, after) if x),
            guide="변경 근거와 관련 도면·사양의 동시 반영 여부를 확인하십시오.",
        ))
    return changes


def _compare_pages(old: DocumentSnapshot, new: DocumentSnapshot) -> tuple[list[PageComparison], list[Change]]:
    page_results: list[PageComparison] = []
    changes: list[Change] = []
    common = min(old.page_count, new.page_count)
    for index in range(common):
        old_page, new_page = old.pages[index], new.pages[index]
        similarity = SequenceMatcher(None, old_page.normalized_text, new_page.normalized_text).ratio()
        visual = visual_difference(old.raw_bytes, new.raw_bytes, index + 1, index + 1)
        if visual >= VISUAL_CHANGE_THRESHOLD:
            status = "시각 변경"
            changes.append(Change(
                category="페이지/도면",
                section=section_for_page(new_page.text, index + 1),
                old_page=index + 1,
                new_page=index + 1,
                item=f"{index + 1}페이지 시각 구성",
                old_value="기존 페이지",
                new_value=f"픽셀 차이 {visual:.1%}",
                change_type="시각 변경",
                confidence="높음",
                evidence="두 페이지 렌더링 비교",
                guide="사진·외형·치수선·도면 요소의 변경 목적과 표 사양 반영 여부를 확인하십시오.",
            ))
        elif old_page.normalized_text != new_page.normalized_text:
            status = "텍스트 변경"
        else:
            status = "동일"
        page_results.append(PageComparison(index + 1, index + 1, similarity, visual, status))

    for page_no in range(common + 1, old.page_count + 1):
        page_results.append(PageComparison(page_no, None, 0.0, 1.0, "삭제"))
        changes.append(Change("페이지", "문서", page_no, None, f"{page_no}페이지", "존재", "-", "삭제"))
    for page_no in range(common + 1, new.page_count + 1):
        page_results.append(PageComparison(None, page_no, 0.0, 1.0, "추가"))
        changes.append(Change("페이지", "문서", None, page_no, f"{page_no}페이지", "-", "존재", "추가"))
    return page_results, changes


def run_quality_checks(document: DocumentSnapshot) -> list[Issue]:
    issues: list[Issue] = []
    all_text = "\n".join(page.text for page in document.pages)
    fields = _field_map(document)
    for required in ("모델번호", "등록번호", "발행일자"):
        if required not in fields:
            issues.append(Issue("문서 검수", "표지", 1, required, "필수항목 누락", "경고", "높음", "항목을 찾지 못함", f"표지에 {required}를 입력하십시오."))

    for typo, (issue_type, severity, guide) in TYPO_RULES.items():
        for page in document.pages:
            if typo in page.text:
                issues.append(Issue("문서 검수", section_for_page(page.text, page.page), page.page, typo, issue_type, severity, "높음", typo, guide))

    if "IIC" in all_text and "I2C" in all_text:
        page_no = next(page.page for page in document.pages if "IIC" in page.text)
        issues.append(Issue(
            "문서 검수", section_for_page(document.pages[page_no - 1].text, page_no), page_no, "IIC / I2C",
            "표기 불일치", "경고", "높음", "문서 내부에서 IIC와 I2C가 함께 사용됨",
            "동일 통신 규격을 뜻한다면 I2C로 통일하고 핀 정의와 하드웨어 사양을 함께 확인하십시오.",
        ))

    current_model = fields.get("모델번호")
    if current_model:
        models = sorted(set(re.findall(r"IEC(?=[A-Z0-9-]*\d)[A-Z0-9-]+", all_text)))
        other_models = [model for model in models if model != current_model.value]
        for model in other_models:
            exact_model = re.compile(rf"(?<![A-Z0-9]){re.escape(model)}(?![A-Z0-9])")
            page = next((p for p in document.pages if exact_model.search(p.text)), document.pages[0])
            issues.append(Issue(
                "문서 검수", section_for_page(page.text, page.page), page.page, "모델 참조",
                "모델·등록번호 불일치", "주의", "중간", model,
                f"현재 모델 {current_model.value}과 다른 참조입니다. 인증 기준모델 등 의도된 참조인지 확인한 뒤 유지 또는 수정하십시오.",
            ))
    return issues


def compare_documents(old: DocumentSnapshot, new: DocumentSnapshot) -> ComparisonResult:
    page_results, page_changes = _compare_pages(old, new)
    field_changes = _compare_fields(old, new)
    issues = run_quality_checks(new)
    return ComparisonResult(old, new, field_changes + page_changes, issues, page_results)
