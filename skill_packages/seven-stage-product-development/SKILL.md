---
name: seven-stage-product-development
description: Plan and deliver a non-trivial software or web application through seven traceable stages—requirements, functional specification, information architecture, wireframes, UI design, implementation, and testing. Use when the user requests a complete development lifecycle, formal project documents, or reusable stage-by-stage deliverables; do not invoke for a small isolated fix or a simple one-file edit.
---

# 7단계 제품 개발

프로젝트의 의사결정과 구현·검증을 하나의 추적 가능한 흐름으로 연결한다. 문서 자체가 목표가 아니라, 구현자가 추가 결정을 하지 않아도 되고 완료 주장을 시험 결과로 검증할 수 있게 만드는 것이 목표다.

## 시작

1. 저장소 지침, 기존 문서, 구현, 테스트, 배포 구성을 먼저 조사한다.
2. 사용자 요청에서 목표, 사용자, 성공 기준, 범위, 제약, 운영 환경을 추출한다. 환경에서 확인할 수 없는 고영향 결정만 질문한다.
3. 현재 모드와 권한을 지킨다. 계획 모드에서는 조사와 계획만 하고 파일을 변경하지 않는다.
4. 기존 산출물이 있으면 새로 만들지 말고 해당 단계부터 갱신한다.
5. 복잡한 신규 프로젝트면 [references/lifecycle.md](references/lifecycle.md)를 읽는다. 요구사항-구현-시험 연결이 중요하면 [references/traceability.md](references/traceability.md)를, 출시 또는 완료 판정이 필요하면 [references/quality-gates.md](references/quality-gates.md)를 추가로 읽는다.

필요하면 다음 명령으로 문서 골격을 만든다. 기존 파일은 덮어쓰지 않는다.

```bash
python scripts/init_development_docs.py --project "프로젝트명" --output docs/development
```

## 실행 원칙

- 기본 단계는 `요구사항 → 기능 → IA → 와이어프레임 → UI → 구현 → 테스트`다. 사용자가 단계별 승인을 요구하면 각 게이트에서 멈추고, 그렇지 않으면 안전한 범위에서 연속 수행한다.
- 모든 기능 요구사항에 안정적인 ID를 부여하고 이후 기능, 구현, 시험에서 같은 ID를 참조한다.
- 사실, 추론, 가정, 미검증을 구분한다. 샘플 데이터 결과를 일반 제품 요구사항으로 과잉 일반화하지 않는다.
- 가장 작은 유지 가능한 구조를 선택한다. 요구되지 않은 계층, 의존성, 계정, 데이터베이스, 배포를 추가하지 않는다.
- 와이어프레임과 UI 시안은 실제 사용자 문구와 핵심 데이터를 사용하고 빈 상태·로딩·오류·성공 상태를 포함한다.
- 구현은 승인된 요구사항과 현재 코드 스타일을 따른다. 무관한 리팩터링을 섞지 않는다.
- 완료 전 관련 테스트, 정적 검사, 빌드, 실제 사용자 흐름을 위험과 비용에 비례해 검증한다. 실행하지 못한 시험은 성공으로 추정하지 않는다.

## 단계별 최소 산출물

| 단계 | 최소 산출물 | 게이트 |
|---|---|---|
| 1. 요구사항 | SRS: 목표, 사용자, 범위, FR/NFR/SEC/DATA, 수용 기준 | 무엇을 만들지 합의됨 |
| 2. 기능 | PRD/FS: 동작 규칙, 상태, 예외, 인터페이스 | 모호한 동작 결정이 없음 |
| 3. IA | 화면/메뉴 구조, 탐색, 상태 보존, 권한별 접근 | 모든 주요 작업 경로가 연결됨 |
| 4. 화면 | 와이어프레임과 화면 명세 | 핵심·빈·오류 흐름을 검토 가능 |
| 5. UI | 디자인 토큰, 컴포넌트, 반응형·접근성 시안 | 구현 가능한 시각 규칙이 확정됨 |
| 6. 개발 | 소스, 구현 기록, 실행·배포 안내 | 요구사항별 구현과 관련 검증 통과 |
| 7. 테스트 | 시험 결과, 결함·재시험, 미검증, 출시 판정 | 근거 기반 완료 또는 명시적 보류 |

문서 형식이 정해지지 않았다면 `assets/templates/`의 템플릿을 사용한다. 대상 조직의 기존 형식이 있으면 그것을 우선한다.

## 검증과 보고

1. `python scripts/validate_traceability.py --docs <문서 폴더>`로 필수 산출물과 요구사항 추적 누락을 점검한다.
2. 변경 파일, 실행한 검사와 결과, 미검증 이유, 남은 위험을 보고한다.
3. Git 저장소라면 사용자가 요청한 경우에만 커밋·푸시한다. 기존 사용자 변경을 되돌리지 않는다.
4. 샘플 출력이나 빌드 산출물은 재현 가치와 저장소 정책을 확인한 뒤 추적 여부를 결정한다.

## 범위 조정

- 작은 수정은 7개 문서를 억지로 만들지 않는다. 기존 요구사항과 시험만 갱신한다.
- 탐색 단계에서 제품 방향이 불명확하면 구현보다 요구사항 게이트를 먼저 확정한다.
- 보안·개인정보·결제·운영 데이터가 포함되면 일반 단순화보다 해당 경계와 실패 안전성을 우선한다.
