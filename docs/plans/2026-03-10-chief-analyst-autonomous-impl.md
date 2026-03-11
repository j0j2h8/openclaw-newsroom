# Chief-Analyst 자율 운영 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** chief-analyst가 매일 3회 정기 브리핑 + 1시간 간격 급등/급락·뉴스 모니터링을 자율 수행

**Architecture:** OpenClaw cron → chief-analyst 에이전트에 메시지 전달 → market_data.py로 데이터 수집 → 분석 → #ai-picks에 deliver

**Tech Stack:** OpenClaw cron, chief-analyst agent, market_data.py, Slack #ai-picks (C0AKAV7QD0W)

---

### Task 1: watchlist.json 생성

**Files:**
- Create: `agents/chief-analyst/workspace/watchlist.json`

**Step 1: 워치리스트 파일 생성**

```json
{
  "stocks": [
    {"symbol": "005930.KS", "name": "삼성전자"},
    {"symbol": "000660.KS", "name": "SK하이닉스"},
    {"symbol": "NVDA", "name": "엔비디아"},
    {"symbol": "AAPL", "name": "애플"}
  ],
  "alertThreshold": 5
}
```

**Step 2: market_data.py로 워치리스트 종목 조회 가능 확인**

Run: `python3 /Users/j/.openclaw/workspace/scripts/market_data.py --symbols 005930.KS 000660.KS NVDA AAPL`
Expected: 4개 종목의 실시간 시세 출력

---

### Task 2: AGENTS.md에 자율 운영 모드 추가

**Files:**
- Modify: `agents/chief-analyst/workspace/AGENTS.md`

**Step 1: AGENTS.md 끝에 자율 운영 섹션 추가**

기존 "# 금지" 섹션 앞에 아래 내용 삽입:

```markdown
# 자율 운영 모드

## 정기 브리핑 (cron에서 호출)
cron이 아래 메시지를 보내면 해당 브리핑을 수행한다:

### "미국장 마감 브리핑"
1. `market_data.py --top 15` 실행
2. 미국 지수(S&P500, 나스닥, 다우) 등락 요약
3. 워치리스트(`watchlist.json`) 미국 종목 변동 점검
4. 내일 한국장 영향 예측
5. Slack mrkdwn으로 응답

### "장 시작 전 브리핑"
1. `market_data.py --top 15` 실행
2. 전일 미국장 마감 요약 (새벽 브리핑과 달라진 점 위주)
3. 당일 한국장 프리뷰 (선물, 환율, 주요 이벤트)
4. 워치리스트 종목 전일 종가 대비 프리마켓/시간외 변동
5. Slack mrkdwn으로 응답

### "장 마감 브리핑"
1. `market_data.py --top 15` 실행
2. 당일 한국 지수(코스피, 코스닥) 등락 요약
3. 워치리스트 전 종목 당일 성과 정리
4. 특이 종목(±3% 이상) 원인 간단 분석
5. 내일 주요 일정/이벤트 예고
6. Slack mrkdwn으로 응답

## 이벤트 감지 (cron에서 호출)

### "워치리스트 점검"
1. `watchlist.json` 읽기
2. `market_data.py --symbols <워치리스트 전 종목>` 실행
3. 각 종목의 전일 종가 대비 변동률 계산
4. ±5% 이상 변동 종목이 있으면: 해당 종목 알림 + 간단 원인 분석
5. 중요 뉴스가 있으면: 핵심 내용 요약
6. **특이사항이 없으면 "특이사항 없음"이라고만 응답한다** — 긴 분석 불필요

## 워치리스트 관리
- 사용자가 "워치리스트에 TSLA 추가해줘" → watchlist.json에 추가
- "워치리스트에서 AAPL 빼줘" → watchlist.json에서 제거
- "워치리스트 보여줘" → 현재 목록 출력
```

---

### Task 3: Cron job 등록 — 정기 브리핑 3개

**Step 1: 미국장 마감 브리핑 (매일 06:00 KST)**

Run:
```
openclaw cron add \
  --name "미국장 마감 브리핑" \
  --agent chief-analyst \
  --cron "0 6 * * 1-5" \
  --tz "Asia/Seoul" \
  --message "미국장 마감 브리핑" \
  --thinking medium \
  --timeout-seconds 300 \
  --session isolated \
  --announce \
  --channel slack \
  --to C0AKAV7QD0W
```

**Step 2: 장 시작 전 브리핑 (매일 08:30 KST)**

Run:
```
openclaw cron add \
  --name "장 시작 전 브리핑" \
  --agent chief-analyst \
  --cron "30 8 * * 1-5" \
  --tz "Asia/Seoul" \
  --message "장 시작 전 브리핑" \
  --thinking medium \
  --timeout-seconds 300 \
  --session isolated \
  --announce \
  --channel slack \
  --to C0AKAV7QD0W
```

**Step 3: 장 마감 브리핑 (매일 16:00 KST)**

Run:
```
openclaw cron add \
  --name "장 마감 브리핑" \
  --agent chief-analyst \
  --cron "0 16 * * 1-5" \
  --tz "Asia/Seoul" \
  --message "장 마감 브리핑" \
  --thinking medium \
  --timeout-seconds 300 \
  --session isolated \
  --announce \
  --channel slack \
  --to C0AKAV7QD0W
```

---

### Task 4: Cron job 등록 — 이벤트 감지 2개

**Step 1: 급등/급락 + 뉴스 점검 (장중 매 1시간, 09~15 KST)**

Run:
```
openclaw cron add \
  --name "워치리스트 점검 (장중)" \
  --agent chief-analyst \
  --cron "0 9-15 * * 1-5" \
  --tz "Asia/Seoul" \
  --message "워치리스트 점검" \
  --thinking medium \
  --timeout-seconds 300 \
  --session isolated \
  --announce \
  --channel slack \
  --to C0AKAV7QD0W
```

**Step 2: 미국장 중 점검 (23:00~05:00 KST, 매 2시간)**

Run:
```
openclaw cron add \
  --name "워치리스트 점검 (미국장)" \
  --agent chief-analyst \
  --cron "0 23,1,3,5 * * 1-5" \
  --tz "Asia/Seoul" \
  --message "워치리스트 점검" \
  --thinking medium \
  --timeout-seconds 300 \
  --session isolated \
  --announce \
  --channel slack \
  --to C0AKAV7QD0W
```

---

### Task 5: 검증 — cron 목록 확인 및 수동 테스트

**Step 1: cron 목록 확인**

Run: `openclaw cron list`
Expected: 5개 job이 모두 enabled 상태로 표시

**Step 2: 수동 테스트 — 장 마감 브리핑**

Run: `openclaw cron run --name "장 마감 브리핑" --json`
Expected: chief-analyst가 market_data.py 실행 → 브리핑 생성 → #ai-picks에 전달

**Step 3: 수동 테스트 — 워치리스트 점검**

Run: `openclaw cron run --name "워치리스트 점검 (장중)" --json`
Expected: 특이사항 없으면 짧은 응답, 있으면 알림

---
