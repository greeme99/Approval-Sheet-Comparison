from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from approval_app.core import PdfValidationError, compare_documents, extract_document, render_page
from approval_app.exporters import export_excel, export_pdf, rows_to_dataframe

st.set_page_config(page_title="Revision Lens | 승인원 비교·검수", page_icon="◫", layout="wide")

st.markdown(
    """
    <style>
    :root {
      --ink: #102A43; --slate: #486581; --mist: #F3F7F9; --line: #C9D7DF;
      --cyan: #00A7A5; --amber: #F3A712; --red: #D64550; --green: #18864B;
    }
    .stApp { background: linear-gradient(90deg, rgba(16,42,67,.035) 1px, transparent 1px),
                          linear-gradient(rgba(16,42,67,.035) 1px, transparent 1px), #F8FAFB;
             background-size: 24px 24px; color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(248,250,251,.92); }
    .block-container { max-width: 1500px; padding-top: 1.4rem; }
    .brandbar { display:flex; align-items:flex-end; justify-content:space-between; border-bottom:3px solid var(--ink); padding-bottom:14px; margin-bottom:24px; }
    .brandbar h1 { margin:0; color:var(--ink); font-family:"Arial Narrow","Segoe UI",sans-serif; font-size:2.35rem; letter-spacing:-.04em; }
    .brandbar p { margin:5px 0 0; color:var(--slate); }
    .stamp { font:700 .75rem/1 "Consolas",monospace; letter-spacing:.12em; color:var(--cyan); border:1px solid var(--cyan); padding:8px 10px; }
    .metric-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:1px; background:var(--line); border:1px solid var(--line); margin:8px 0 20px; }
    .metric-cell { background:white; padding:14px 16px; }
    .metric-cell span { color:var(--slate); font-size:.78rem; }
    .metric-cell strong { display:block; color:var(--ink); font:700 1.55rem/1.2 "Consolas",monospace; margin-top:4px; }
    .local-note { border-left:4px solid var(--cyan); background:#EAF8F7; padding:10px 14px; color:#174F58; margin-bottom:14px; }
    .upload-label { font:700 .8rem/1 "Consolas",monospace; color:var(--slate); letter-spacing:.08em; }
    .stButton > button, .stDownloadButton > button { border-radius:3px; border:1px solid var(--ink); font-weight:700; }
    .stButton > button[kind="primary"] { background:var(--ink); color:white; }
    div[data-baseweb="tab-list"] { border-bottom:1px solid var(--line); gap:6px; }
    div[data-baseweb="tab"] { font-weight:700; }
    [data-testid="stMetric"] { background:white; border:1px solid var(--line); padding:12px; }
    @media (max-width: 900px) { .metric-strip { grid-template-columns:repeat(2,1fr); } .stamp { display:none; } }
    @media (prefers-reduced-motion: reduce) { * { scroll-behavior:auto !important; transition:none !important; animation:none !important; } }
    </style>
    <div class="brandbar">
      <div><h1>REVISION LENS</h1><p>승인원 변경과 문서 품질을 한 근거 화면에서 검토합니다.</p></div>
      <div class="stamp">LOCAL · DETERMINISTIC · V1.0</div>
    </div>
    <div class="local-note"><b>로컬 처리</b> · 업로드한 PDF와 분석 결과는 외부 서버로 전송되지 않습니다.</div>
    """,
    unsafe_allow_html=True,
)


def analysis_key(old_bytes: bytes, new_bytes: bytes) -> str:
    return hashlib.sha256(old_bytes + new_bytes).hexdigest()


def reset_analysis() -> None:
    for key in ("result", "review_df", "analysis_key"):
        st.session_state.pop(key, None)


left_upload, right_upload = st.columns(2)
with left_upload:
    st.markdown('<div class="upload-label">OLD / 기준 승인원</div>', unsafe_allow_html=True)
    old_file = st.file_uploader("기준 승인원 PDF", type=["pdf"], key="old_pdf", label_visibility="collapsed")
with right_upload:
    st.markdown('<div class="upload-label">NEW / 개정 승인원</div>', unsafe_allow_html=True)
    new_file = st.file_uploader("개정 승인원 PDF", type=["pdf"], key="new_pdf", label_visibility="collapsed")

action_col, hint_col = st.columns([1, 4])
with action_col:
    analyze = st.button("두 승인원 분석", type="primary", width="stretch", disabled=not (old_file and new_file))
with hint_col:
    st.caption("텍스트 객체가 포함된 디지털 PDF를 지원합니다. 암호화·스캔 PDF는 분석 전에 안내합니다.")

if analyze and old_file and new_file:
    old_bytes, new_bytes = old_file.getvalue(), new_file.getvalue()
    try:
        with st.spinner("문서 구조, 사양, 페이지 렌더링을 비교하고 있습니다…"):
            old_document = extract_document(old_bytes, old_file.name)
            new_document = extract_document(new_bytes, new_file.name)
            result = compare_documents(old_document, new_document)
            st.session_state.result = result
            st.session_state.analysis_key = analysis_key(old_bytes, new_bytes)
            st.session_state.review_df = pd.DataFrame([row.to_dict() for row in result.review_rows])
    except PdfValidationError as exc:
        reset_analysis()
        st.error(str(exc))
    except Exception as exc:
        reset_analysis()
        st.error(f"분석 중 처리할 수 없는 오류가 발생했습니다: {exc}")

result = st.session_state.get("result")
if not result:
    st.info("기준 승인원과 개정 승인원을 선택하면 변경표, 페이지 비교, 수정 가이드를 생성합니다.")
    st.stop()

review_df: pd.DataFrame = st.session_state.review_df
counts = review_df["change_type"].value_counts().to_dict()
st.markdown(
    f"""
    <div class="metric-strip">
      <div class="metric-cell"><span>전체 검토 항목</span><strong>{len(review_df)}</strong></div>
      <div class="metric-cell"><span>사양·식별 변경</span><strong>{len(result.changes)}</strong></div>
      <div class="metric-cell"><span>문서 품질 문제</span><strong>{len(result.issues)}</strong></div>
      <div class="metric-cell"><span>시각 변경 페이지</span><strong>{counts.get('시각 변경', 0)}</strong></div>
    </div>
    """,
    unsafe_allow_html=True,
)

summary_tab, page_tab, issue_tab, export_tab = st.tabs(["변경 요약", "페이지 근거", "문제 검토", "보고서"])

with summary_tab:
    filter_a, filter_b, filter_c = st.columns(3)
    with filter_a:
        type_filter = st.multiselect("변경 유형", sorted(review_df["change_type"].dropna().unique()), placeholder="전체")
    with filter_b:
        severity_filter = st.multiselect("심각도", sorted(review_df["severity"].dropna().unique()), placeholder="전체")
    with filter_c:
        status_filter = st.multiselect("검토 상태", ["보류", "승인", "반려"], placeholder="전체")

    mask = pd.Series(True, index=review_df.index)
    if type_filter:
        mask &= review_df["change_type"].isin(type_filter)
    if severity_filter:
        mask &= review_df["severity"].isin(severity_filter)
    if status_filter:
        mask &= review_df["review_status"].isin(status_filter)
    filtered = review_df.loc[mask].copy()
    edited = st.data_editor(
        filtered,
        width="stretch",
        hide_index=True,
        disabled=[column for column in filtered.columns if column not in ("review_status", "review_comment")],
        column_config={
            "category": st.column_config.TextColumn("구분"),
            "section": st.column_config.TextColumn("섹션"),
            "old_page": st.column_config.NumberColumn("구 P."),
            "new_page": st.column_config.NumberColumn("신 P."),
            "item": st.column_config.TextColumn("항목"),
            "old_value": st.column_config.TextColumn("기존값"),
            "new_value": st.column_config.TextColumn("변경값"),
            "change_type": st.column_config.TextColumn("변경 유형"),
            "issue_type": st.column_config.TextColumn("문제 유형"),
            "severity": st.column_config.TextColumn("심각도"),
            "confidence": st.column_config.TextColumn("신뢰도"),
            "evidence": st.column_config.TextColumn("원문 근거"),
            "guide": st.column_config.TextColumn("수정 가이드", width="large"),
            "review_status": st.column_config.SelectboxColumn("검토 상태", options=["보류", "승인", "반려"], required=True),
            "review_comment": st.column_config.TextColumn("검토 의견", width="large"),
        },
        column_order=["category", "section", "old_page", "new_page", "item", "old_value", "new_value", "change_type", "issue_type", "severity", "confidence", "guide", "review_status", "review_comment"],
        key="review_editor",
    )
    review_df.loc[edited.index, ["review_status", "review_comment"]] = edited[["review_status", "review_comment"]]
    st.session_state.review_df = review_df

with page_tab:
    page_numbers = [page.new_page or page.old_page for page in result.pages]
    selected_page = st.selectbox("비교할 페이지", page_numbers, format_func=lambda value: f"{value}페이지")
    page_info = next(page for page in result.pages if (page.new_page or page.old_page) == selected_page)
    st.caption(f"판정: {page_info.status} · 텍스트 유사도 {page_info.text_similarity:.1%} · 시각 차이율 {page_info.visual_difference:.2%}")
    old_col, new_col = st.columns(2)
    with old_col:
        st.markdown("**OLD · 기준본**")
        if page_info.old_page:
            st.image(render_page(result.old_document.raw_bytes, page_info.old_page), width="stretch")
        else:
            st.info("기준본에는 대응 페이지가 없습니다.")
    with new_col:
        st.markdown("**NEW · 개정본**")
        if page_info.new_page:
            st.image(render_page(result.new_document.raw_bytes, page_info.new_page), width="stretch")
        else:
            st.info("개정본에는 대응 페이지가 없습니다.")

with issue_tab:
    issue_rows = review_df[review_df["issue_type"].astype(str).ne("")]
    if issue_rows.empty:
        st.success("현재 규칙으로 탐지된 오류·누락·표기 불일치가 없습니다.")
    else:
        for _, row in issue_rows.iterrows():
            with st.expander(f"{row['severity']} · {row['issue_type']} · {row['item']}", expanded=row["severity"] == "경고"):
                st.write(row["guide"])
                st.caption(f"{row['section']} / {row['new_page']}페이지 · 근거: {row['evidence']} · 신뢰도: {row['confidence']}")

with export_tab:
    approved = int((review_df["review_status"] == "승인").sum())
    rejected = int((review_df["review_status"] == "반려").sum())
    pending = int((review_df["review_status"] == "보류").sum())
    a, b, c = st.columns(3)
    a.metric("승인", approved)
    b.metric("반려", rejected)
    c.metric("보류", pending)
    if pending:
        st.warning("보류 항목이 포함된 중간 보고서입니다. 최종 배포 전에 검토 상태를 확정하십시오.")
    rows = review_df.to_dict(orient="records")
    excel_data = export_excel(result, rows)
    pdf_data = export_pdf(result, rows)
    download_a, download_b = st.columns(2)
    download_a.download_button("Excel 보고서 다운로드", excel_data, "승인원_비교검수_보고서.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    download_b.download_button("PDF 보고서 다운로드", pdf_data, "승인원_비교검수_보고서.pdf", "application/pdf", width="stretch")
    st.caption("보고서에는 파일 해시, 처리 버전, 추출 품질과 검토 상태가 함께 기록됩니다.")
