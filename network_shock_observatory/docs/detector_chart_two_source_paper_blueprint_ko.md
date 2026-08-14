# Detector–MDOT CHART 두 자료 기반 Key Bridge 운영회복력 논문 설계

## 1. 두 자료는 무엇이 다른가?

두 자료는 서로 다른 것을 관측하므로, 함께 쓰면 단순히 표본을 늘리는 것이 아니라 **교통 결과와 운영 맥락을 연결**할 수 있다.

| 구분 | Detector panel | MDOT CHART event log |
| --- | --- | --- |
| 관측 대상 | 특정 도로·차로/zone의 교통상태 | 사고, 고장차, 공사, 장애물, 차로폐쇄, 기상성·특별 사건 |
| 기본 단위 | `zone × 5분` 원자료, `zone × 15분` 분석패널 | `event × 시작시각 × 종료시각 × 위치` |
| 핵심 변수 | speed, volume, occupancy, quality | standardized type, location, start/closed time, duration, responders, max lanes closed |
| 연구 역할 | **결과변수**: 속도·교통량·신뢰성·peak congestion | **운영 맥락·교란 진단·메커니즘 결과**: 사건, 공사, 차로폐쇄 burden |
| 시간 범위 | 2022–2024 | 2020–2024 |

> **핵심 원칙:** Detector는 “교통이 어떻게 변했는가”를 측정하고, CHART는 “그 시간·장소에 교통 운영을 바꿀 다른 사건이 있었는가”를 기록한다. CHART를 detector의 중복 데이터로 보거나, 모든 CHART 사건을 자동 통제변수로 넣으면 안 된다.

---

## 2. 제안 논문

### 권장 제목

**Operational Resilience after the Francis Scott Key Bridge Collapse: Integrating High-Frequency Traffic Detectors with Incident Management Logs**

### 중심 연구 질문

> **2024년 3월 26일 Key Bridge 붕괴 이후, MDTA가 지정한 I-95/I-895 터널 접근 회랑은 사전 동학 및 비교 회랑에 비해 어떤 속도·교통량·첨두 신뢰성 변화를 보였으며, 이 변화는 동시 발생한 비교량 사건·공사·차로폐쇄와 구별되는가?**

### 논문의 독창성

이 논문은 LODES 기반 장기 접근성·형평성 분석과 달리, **15분 detector 관측자료와 실시간 incident-management 기록을 결합해 급성 네트워크 충격의 운영회복력**을 평가한다. 핵심 기여는 “사건을 모두 통제하는 회귀”가 아니라, 다음을 분리하는 투명한 설계다.

1. Key Bridge 붕괴의 **총 운영 영향**: detector 속도·교통량 변화.
2. 동시 비교량 사건의 **교란 가능성**: CHART 기반 severe incident/roadwork 민감도.
3. 운영부담의 **메커니즘적 맥락**: CHART collision, disabled vehicle, obstruction, lane closure burden의 시간·회랑 분포.

---

## 3. 통합 분석 데이터셋

### 3.1 기본 시간·공간 단위

분석 단위는 `detector zone × 15분`이다. detector 원자료를 `America/New_York` 시간대에서 15분으로 집계하고, CHART event의 활성 구간을 같은 bin에 겹친다. 일별 결과는 15분 bin에서 파생하되, 논문의 주 분석은 첨두시간대를 잃지 않도록 15분 또는 시간대별 결과를 유지한다.

| 계층 | 주 키 | 내용 | 검증 규칙 |
| --- | --- | --- | --- |
| Detector base | `zone_id, local_15min` | speed, volume, occupancy, quality, lane availability | 음수 교통량 제외, 속도 범위·flatline·결측 플래그 유지 |
| Zone geography | `zone_id` | road label, direction, lat/lon, nearest OSM/MDOT link | 수동 표본 QA, 방향 불일치 제외 |
| CHART event | `event_id 또는 row_id, start, close` | type, location, responders, lane closure, duration | offset-aware 시간 파싱, close 결측 별도 표시 |
| Corridor-time burden | `corridor, local_15min` | active collision/roadwork/disabled vehicle/obstruction, event minutes, lane closure observed | 사건유형별로 분리; 차로폐쇄 결측을 0으로 대체하지 않음 |

### 3.2 공간 결합 단계

현재 CHART는 `Location` 텍스트를 제공한다. 따라서 즉시 가능한 1단계 결합은 **사전 정의한 회랑 × 15분** 결합이다. I-95/I-895 접근 회랑과 I-83/I-795 비교 회랑에 대해 location 문구의 도로·방향·마일포스트를 구조화한다. 이 단계는 정확한 zone 수준 결합이 아니므로, 논문에 “corridor-level operational context”라고 명시해야 한다.

2단계에서는 CHART event geometry, 마일포스트, 또는 authoritative roadway locator를 확보해 detector anchor의 0.5–1.0 mile 이내·동방향 이벤트만 연결한다. 이때 location parsing 정확도(무작위 표본 100건의 정확·부정확·불확정 비율)를 부록에 제시한다.

---

## 4. 식별 및 추정 전략

### 4.1 주 분석: 총 운영효과의 Augmented Synthetic Control / SDID

주 결과는 detector로만 측정한다. 처리단위는 I-95/I-895 접근 zone의 속도·교통량 가중 회랑 평균이고, donor pool은 I-83/I-795 및 사전 지정된 비항만·비연결 고속도로 zone이다. Key Bridge 접근부·I-695 남동부·직접 우회경로는 donor pool에서 제외한다.

실제 Augmented Synthetic Control(ASCM) 또는 Synthetic Difference-in-Differences(SDID)는 다음을 반드시 산출한다.

| 항목 | 투고용 최소 산출물 |
| --- | --- |
| 사전 fitting 기간 | 2024-02-12~2024-03-25 평일 15분/시간대 결과 |
| outcome | volume-weighted speed, log volume, PM speed, speed reliability |
| donor selection | 사전 공표된 제외규칙, detector availability, spatial separation |
| fit 품질 | RMSPE, donor weights, pre-gap plot |
| 사후 효과 | event-time gap, 1·2·4주 평균 ATT, zone/block bootstrap 또는 randomization inference |
| 위약 | in-space donor placebo, in-time pre-event placebo, leave-one-donor-out |

CHART의 사후 collision·disabled vehicle·congestion은 붕괴의 매개경로일 수 있으므로 **주 ASCM/SDID의 자동 통제변수가 아니다.** 주 추정량은 교량 붕괴가 처리 회랑 운영에 미친 총효과로 정의한다.

### 4.2 보조 분석: CHART 기반 교란 민감도

CHART는 “교량 붕괴 외의 큰 운영사건이 처리·비교 회랑에 다르게 집중돼 주 효과를 왜곡했는가?”를 평가하는 데 사용한다. 다음 세 개의 사전 지정된 보조표본을 보고한다.

1. **All observations:** 주 분석과 동일한 모든 유효 detector bin.
2. **Non-bridge severe-event excluded:** active roadwork, explicit lane closure, flood/strong wind, 또는 장시간 non-bridge event가 있는 bin/day 제외.
3. **Context-adjusted model:** severe event count, observed lanes closed, roadwork indicator를 보조 회귀/augmented outcome model에 포함.

세 모형의 ATT 방향과 크기가 유사하면, 관측된 교통악화가 단순 공사·사고 차이에만 의존하지 않는다는 증거가 된다. 반대로 크기가 크게 달라지면, 이를 “CHART 사건으로 설명되는 운영 환경 차이”로 정직하게 해석한다.

### 4.3 메커니즘·운영 결과: CHART 자체를 결과변수로 사용

다음 분석은 총효과 주장을 보완하는 운영결과다.

\[
B_{c,t}=\sum_e \mathbb{1}(s_e\le t<c_e)\mathbb{1}(e\in c),
\]

여기서 \(B_{c,t}\)는 회랑 \(c\)에서 활성화된 사건 burden이다. collision, disabled vehicle, obstruction, roadwork, lane-closure event를 각각 분리해 처리·비교 회랑의 event-time profile을 제시한다. 이는 “사후 detector 속도저하와 사건 부담이 동반되었는가?”라는 설명적 질문에 답하지만, 사고 증가를 붕괴의 인과적 안전효과로 단정하지 않는다.

---

## 5. 원고 구성

### Introduction

Key Bridge 붕괴의 제도적 충격, 공식 I-95/I-895 우회지침, 그리고 고빈도 운영 모니터링의 필요성을 제시한다. 기존 접근성·형평성 연구와 달리 이 원고는 “운영회복력과 incident-aware counterfactual”에 집중한다고 분명히 쓴다.

### Literature Review

교량·네트워크 충격, detector 기반 운영회복력, incident-management data 활용, synthetic control/SDID, spatial interference를 검토한다. 기존 Key Bridge 접근성 연구는 상호 보완적 선행연구로 인용하되, 센서·사건 로그 결합과 15분 운영결과가 차별점임을 제시한다.

### Data

Detector와 CHART를 별도 표로 제시한다. CHART의 location text, 차로폐쇄 결측, 2023 detector의 3월 27일 이후 커버리지라는 제약을 투명하게 밝힌다.

### Methods

주 ASCM/SDID, donor/exclusion 규칙, total-effect estimand, CHART sensitivity design, CHART event-burden descriptives, uncertainty·위약검정을 순서대로 설명한다.

### Results and Discussion

먼저 pre-fit과 주 detector ATT를 제시한다. 다음으로 CHART severe-event 제외·보조통제 결과를 제시한다. 마지막으로 CHART event burden이 처리 회랑에서 어떻게 달라졌는지 보여 주고, 총효과·교란·매개경로를 구분해 DOT 운영 시사점을 논의한다.

### Conclusion

공식 우회 회랑의 운영부담, detector와 incident log의 상호보완성, 비상운영 모니터링 개선안을 요약한다. 개별 차량 OD, 완전한 2023 사전기간, 정확한 event geometry, 2024 crash report 부재를 한계로 밝힌다.

---

## 6. 제출용 표·그림 목록

| 번호 | 산출물 | 목적 |
| ---: | --- | --- |
| Figure 1 | 연구지역·처리/비교/donor 회랑·detector zone·CHART event timeline 지도 | 사전 지정 공간 설계 공개 |
| Figure 2 | detector panel availability와 CHART active-event coverage | 자료 품질과 관측 범위 |
| Figure 3 | ASCM/SDID 사전 fit과 event-time speed/log-volume gap | 주 결과 |
| Figure 4 | in-space/in-time placebo RMSPE 비율 분포 | 식별 강건성 |
| Figure 5 | 처리·비교 회랑의 CHART collision/roadwork/lane-closure burden | 운영 메커니즘 맥락 |
| Table 1 | Detector·CHART 데이터 사전 및 품질 규칙 | 재현성 |
| Table 2 | 회랑·donor 구성과 사전기간 balance | 설계 투명성 |
| Table 3 | 주 ATT: 1·2·4주, speed·volume·reliability | 핵심 결과 |
| Table 4 | All / severe-event excluded / context-adjusted 민감도 | CHART 활용의 핵심 |
| Table 5 | 위약, leave-one-out, alternative time windows | 강건성 |

---

## 7. 즉시 실행할 작업

1. CHART 2023·2024의 `Location`을 road/direction/milepost로 구조화하고, 처리·비교 회랑 분류표를 만든다.
2. 15분 active-incident burden panel을 생성한다.
3. detector panel에 corridor-time CHART burden을 left join하고, 결측·공간 매칭 QA 표를 만든다.
4. 실제 ASCM/SDID를 구현한다. 현재 이전 원고에 있던 단순 회랑 사전·사후 gap은 SCM으로 부르지 않는다.
5. 주모형과 CHART 민감도 모형을 모두 실행한 뒤, 결과에 따라 6,000자 원고를 최종 작성한다.
