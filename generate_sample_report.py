"""제공된 N/NB1 샘플로 검증용 보고서를 생성한다."""

from pathlib import Path

from approval_app.core import compare_documents, extract_document
from approval_app.exporters import export_excel, export_pdf


def main() -> None:
    root = Path(__file__).resolve().parent
    output = root / "sample_outputs"
    output.mkdir(exist_ok=True)
    old = extract_document((root / "IEC1000-07N.pdf").read_bytes(), "IEC1000-07N.pdf")
    new = extract_document((root / "IEC1000-07NB1.pdf").read_bytes(), "IEC1000-07NB1.pdf")
    result = compare_documents(old, new)
    rows = [row.to_dict() for row in result.review_rows]
    (output / "IEC1000-07N_vs_IEC1000-07NB1_비교검수.xlsx").write_bytes(export_excel(result, rows))
    (output / "IEC1000-07N_vs_IEC1000-07NB1_비교검수.pdf").write_bytes(export_pdf(result, rows))
    print(f"변경 {len(result.changes)}건, 품질 검수 {len(result.issues)}건")


if __name__ == "__main__":
    main()

