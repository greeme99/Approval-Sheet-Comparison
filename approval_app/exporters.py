from __future__ import annotations

import io
import os
from copy import copy
from datetime import datetime
from html import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .core import APP_VERSION
from .models import ComparisonResult

REPORT_COLUMNS = [
    "구분", "섹션", "구페이지", "신페이지", "항목명", "기존값", "변경값", "변경 유형",
    "문제 유형", "심각도", "신뢰도", "원문 근거", "수정 가이드", "검토 상태", "검토 의견",
]


def rows_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    mapped = []
    for row in rows:
        mapped.append({
            "구분": row.get("category", ""),
            "섹션": row.get("section", ""),
            "구페이지": row.get("old_page", ""),
            "신페이지": row.get("new_page", ""),
            "항목명": row.get("item", ""),
            "기존값": row.get("old_value", ""),
            "변경값": row.get("new_value", ""),
            "변경 유형": row.get("change_type", ""),
            "문제 유형": row.get("issue_type", ""),
            "심각도": row.get("severity", ""),
            "신뢰도": row.get("confidence", ""),
            "원문 근거": row.get("evidence", ""),
            "수정 가이드": row.get("guide", ""),
            "검토 상태": row.get("review_status", "보류"),
            "검토 의견": row.get("review_comment", ""),
        })
    return pd.DataFrame(mapped, columns=REPORT_COLUMNS)


def export_excel(result: ComparisonResult, rows: list[dict]) -> bytes:
    output = io.BytesIO()
    review_df = rows_to_dataframe(rows)
    page_df = pd.DataFrame([
        {
            "구페이지": page.old_page,
            "신페이지": page.new_page,
            "텍스트 유사도": page.text_similarity,
            "시각 차이율": page.visual_difference,
            "판정": page.status,
        }
        for page in result.pages
    ])
    metadata_df = pd.DataFrame([
        ["앱 버전", APP_VERSION, APP_VERSION],
        ["파일명", result.old_document.filename, result.new_document.filename],
        ["SHA-256", result.old_document.sha256, result.new_document.sha256],
        ["페이지 수", result.old_document.page_count, result.new_document.page_count],
        ["추출 품질", result.old_document.extraction_quality, result.new_document.extraction_quality],
        ["처리 시각", datetime.now().astimezone().isoformat(timespec="seconds"), ""],
    ], columns=["항목", "구버전", "신버전"])

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        review_df.to_excel(writer, sheet_name="변경 및 검수", index=False)
        page_df.to_excel(writer, sheet_name="페이지 비교", index=False)
        metadata_df.to_excel(writer, sheet_name="처리 정보", index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                width = min(max(len(str(cell.value or "")) for cell in column) + 2, 48)
                sheet.column_dimensions[column[0].column_letter].width = width
                for cell in column:
                    alignment = copy(cell.alignment)
                    alignment.vertical = "top"
                    alignment.wrap_text = True
                    cell.alignment = alignment
    return output.getvalue()


def _register_korean_font() -> str:
    candidates = [
        os.environ.get("APPROVAL_APP_FONT", ""),
        r"C:\Windows\Fonts\malgun.ttf",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("ApprovalKorean", path))
                return "ApprovalKorean"
            except Exception:
                continue
    return "Helvetica"


def export_pdf(result: ComparisonResult, rows: list[dict]) -> bytes:
    output = io.BytesIO()
    font = _register_korean_font()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleKo", parent=styles["Title"], fontName=font, fontSize=20, leading=26, textColor=colors.HexColor("#102A43"))
    body_style = ParagraphStyle("BodyKo", parent=styles["BodyText"], fontName=font, fontSize=8, leading=11, alignment=TA_LEFT)
    small_style = ParagraphStyle("SmallKo", parent=body_style, fontSize=7, leading=9)
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    story = [Paragraph("승인원 변경·검수 보고서", title_style), Spacer(1, 4 * mm)]
    metadata = [
        ["구버전", result.old_document.filename, "신버전", result.new_document.filename],
        ["구버전 SHA-256", result.old_document.sha256, "신버전 SHA-256", result.new_document.sha256],
        ["처리 버전", APP_VERSION, "추출 품질", f"{result.old_document.extraction_quality} / {result.new_document.extraction_quality}"],
    ]
    meta_table = Table([[Paragraph(escape(str(cell)), small_style) for cell in row] for row in metadata], colWidths=[28 * mm, 88 * mm, 30 * mm, 100 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E9F2F7")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E9F2F7")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C7D1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.extend([meta_table, Spacer(1, 5 * mm)])

    frame = rows_to_dataframe(rows)
    display_columns = ["구분", "신페이지", "항목명", "기존값", "변경값", "변경 유형", "심각도", "수정 가이드", "검토 상태", "검토 의견"]
    table_data = [[Paragraph(escape(column), small_style) for column in display_columns]]
    for _, row in frame[display_columns].iterrows():
        table_data.append([Paragraph(escape(str(value if pd.notna(value) else "")), small_style) for value in row])
    if len(table_data) == 1:
        table_data.append([Paragraph("변경 또는 검수 항목이 없습니다.", small_style)] + [""] * (len(display_columns) - 1))
    table = Table(table_data, repeatRows=1, colWidths=[18 * mm, 14 * mm, 30 * mm, 34 * mm, 34 * mm, 20 * mm, 17 * mm, 56 * mm, 20 * mm, 32 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102A43")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C7D1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
    ]))
    story.append(table)
    story.extend([PageBreak(), Paragraph("판정 안내", title_style), Spacer(1, 3 * mm)])
    story.append(Paragraph(
        "이 보고서는 디지털 PDF에서 추출한 텍스트·좌표·렌더링 결과를 규칙으로 비교합니다. "
        "‘검토 필요’ 항목은 자동 오류 확정이 아니며, 원본 문서와 설계·인증 근거를 대조해 최종 판단해야 합니다.",
        body_style,
    ))
    doc.build(story)
    return output.getvalue()
