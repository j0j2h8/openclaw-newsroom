# Chief-Analyst 자율 운영 시스템 설계

## 개요
chief-analyst 팀을 24시간 자율 운영으로 전환한다.
정기 루틴(브리핑 3회/일) + 이벤트 감지(급등/급락, 뉴스 속보)를 cron 기반으로 구현.

## 정기 루틴

| 루틴 | 스케줄 | 프롬프트 | 데이터 |
|------|--------|---------|--------|
| 미국장 마감 브리핑 | 매일 06:00 | "미국장 마감 브리핑" | --top 15 |
| 장 시작 전 브리핑 | 매일 08:30 | "장 시작 전 브리핑" | --top 15 |
| 장 마감 브리핑 | 매일 16:00 | "장 마감 브리핑" | --top 15 + watchlist |

결과는 --deliver로 #ai-picks (C0AKAV7QD0W)에 전달.

## 이벤트 감지

| 감지 | 스케줄 | 조건 | 동작 |
|------|--------|------|------|
| 급등/급락 | 매 1시간 (장중 09~15 KST) | watchlist 종목 ±5% | 알림 |
| 뉴스 속보 | 매 1시간 | watchlist 종목 중요 뉴스 | 알림 |

특이사항 없으면 응답하지 않는다 (무응답 = 정상).

## 워치리스트

`agents/chief-analyst/workspace/watchlist.json`에 저장.
사용자가 #ai-picks에서 자연어로 추가/제거 가능.

초기 목록: 삼성전자, SK하이닉스, NVDA, AAPL

## 변경 파일

- `cron/jobs.json` — 5개 cron job 추가
- `agents/chief-analyst/workspace/AGENTS.md` — 루틴/모니터링 모드 지침 추가
- `agents/chief-analyst/workspace/watchlist.json` — 신규
- `agents/chief-analyst/workspace/HEARTBEAT.md` — 비워둠 (cron으로 대체)

## 리스크

- 토큰 비용: 하루 5~8회 호출
- "특이사항 없으면 무응답" 동작 검증 필요
- 뉴스 감지 시 sub-agent 호출 지연 가능
