# Revision Lens — 승인원 비교·검수 앱

[![CI](https://github.com/greeme99/Approval-Sheet/actions/workflows/ci.yml/badge.svg)](https://github.com/greeme99/Approval-Sheet/actions/workflows/ci.yml)

두 디지털 PDF 승인원의 식별정보·사양·페이지 시각 변경을 비교하고, 로컬 규칙으로 오류·누락·표기 불일치 수정 가이드를 제공하는 Windows용 로컬 앱입니다.

## 주요 기능

- 모델번호, 등록번호, 발행일자와 알려진 사양 항목 비교
- 추가·삭제·수정 및 3% 이상 페이지 시각 변경 탐지
- 필수항목, 오타, IIC/I2C, 모델 참조 등 로컬 품질 검사
- 원문 페이지 좌우 검토와 승인·반려·보류 의견
- Excel 및 한글 PDF 보고서 다운로드
- 파일 해시, 앱 버전, 추출 품질 기록

## 개발 환경 실행

Python 3.11 환경에서 다음 순서로 실행합니다.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

브라우저가 `http://127.0.0.1:8501`을 엽니다. 앱은 외부 AI API나 외부 서버를 사용하지 않습니다.

## Windows 패키지 생성

Windows 10/11에서 `build_windows.bat`를 실행합니다. 완료 후 `dist\RevisionLens\RevisionLens.exe`를 실행하십시오. `one-folder` 배포이므로 `RevisionLens` 폴더 전체를 함께 배포해야 하며 내부 파일을 분리하면 실행되지 않습니다.

## 사용 순서

1. `OLD`에 기준 승인원, `NEW`에 개정 승인원을 선택합니다.
2. `두 승인원 분석`을 누릅니다.
3. 변경 요약에서 필터로 항목을 좁히고 검토 상태·의견을 입력합니다.
4. 페이지 근거에서 원문과 차이율을 확인합니다.
5. 문제 검토에서 수정 가이드를 확인합니다.
6. 보고서 탭에서 Excel 또는 PDF를 내려받습니다.

## 지원 범위와 제한

- v1은 텍스트 객체가 포함된 비암호화 디지털 PDF용입니다.
- 스캔 PDF OCR, 복잡한 중간 페이지 재배열 자동 매칭, 자동 원본 수정은 지원하지 않습니다.
- 사양 키는 `approval_app/core.py`의 로컬 사전으로 확장할 수 있습니다.
- 자동 품질 검사는 수정 후보입니다. 인증 기준모델 같은 의도된 참조는 원본 근거를 확인한 뒤 최종 판단하십시오.

## 산출물

- `01_SRS_요구사항명세서.md`
- `02_PRD_FS_기능명세서.md`
- `03_IA_정보구조.md`
- `04_와이어프레임.html`
- `05_UI디자인시안.html`
- `app.py`, `approval_app/`, `build_windows.bat`
- `07_테스트결과보고서.md`

