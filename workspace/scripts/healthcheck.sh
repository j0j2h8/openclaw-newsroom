#!/bin/bash
# OpenClaw 시스템 헬스체크
# 게이트웨이, 크론, Slack 연결 상태를 점검하고 이상 시 리포트 출력

ISSUES=()

# 1. 게이트웨이 프로세스 확인
GW_STATUS=$(openclaw gateway status 2>&1)
if echo "$GW_STATUS" | grep -q "Runtime: running"; then
  GW_OK=true
else
  GW_OK=false
  ISSUES+=("게이트웨이 프로세스가 실행 중이 아닙니다")
fi

# 2. RPC 프로브 확인
if echo "$GW_STATUS" | grep -q "RPC probe: ok"; then
  RPC_OK=true
else
  RPC_OK=false
  ISSUES+=("게이트웨이 RPC 프로브 실패")
fi

# 3. 크론 스케줄러 상태
CRON_STATUS=$(openclaw cron status 2>&1)
if echo "$CRON_STATUS" | grep -q '"enabled": true'; then
  CRON_OK=true
  CRON_JOBS=$(echo "$CRON_STATUS" | grep -o '"jobs": [0-9]*' | grep -o '[0-9]*')
else
  CRON_OK=false
  CRON_JOBS=0
  ISSUES+=("크론 스케줄러가 비활성 상태입니다")
fi

# 4. 크론 작업 오류 확인
CRON_LIST=$(openclaw cron list --json 2>&1)
ERROR_JOBS=$(echo "$CRON_LIST" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    jobs = data if isinstance(data, list) else data.get('jobs', [])
    errors = []
    for j in jobs:
        state = j.get('state', {})
        consec = state.get('consecutiveErrors', 0)
        # 1회 오류는 API 일시 장애일 수 있으므로 무시. 2회 연속부터 알림
        if consec >= 2:
            errors.append(f\"{j.get('name', '?')} (에러 {consec}회 연속)\")
    if errors:
        print('\n'.join(errors))
except:
    pass
" 2>/dev/null)

if [ -n "$ERROR_JOBS" ]; then
  while IFS= read -r line; do
    ISSUES+=("크론 오류: $line")
  done <<< "$ERROR_JOBS"
fi

# 5. 최근 배달 실패 확인
DELIVERY_FAILS=$(echo "$CRON_LIST" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    jobs = data if isinstance(data, list) else data.get('jobs', [])
    fails = []
    for j in jobs:
        state = j.get('state', {})
        ds = state.get('lastDeliveryStatus', '')
        ls = state.get('lastStatus', '')
        if ds == 'error' and ls == 'ok':
            fails.append(j.get('name', '?'))
    if fails:
        print('\n'.join(fails))
except:
    pass
" 2>/dev/null)

if [ -n "$DELIVERY_FAILS" ]; then
  while IFS= read -r line; do
    ISSUES+=("배달 실패: $line")
  done <<< "$DELIVERY_FAILS"
fi

# 6. 디스크 사용량 (로그 비대화 방지)
LOG_SIZE=$(du -sm /Users/j/.openclaw/logs/ 2>/dev/null | awk '{print $1}')
if [ -n "$LOG_SIZE" ] && [ "$LOG_SIZE" -gt 500 ]; then
  ISSUES+=("로그 디렉토리 ${LOG_SIZE}MB — 정리 필요")
fi

SESSION_SIZE=$(du -sm /Users/j/.openclaw/agents/ 2>/dev/null | awk '{print $1}')
if [ -n "$SESSION_SIZE" ] && [ "$SESSION_SIZE" -gt 1000 ]; then
  ISSUES+=("에이전트 세션 ${SESSION_SIZE}MB — 정리 필요")
fi

# 결과 출력
if [ ${#ISSUES[@]} -eq 0 ]; then
  echo "HEALTHCHECK_OK"
else
  echo "ISSUES_FOUND"
  echo "---"
  for issue in "${ISSUES[@]}"; do
    echo "- $issue"
  done
  echo "---"
  echo "GW=$GW_OK RPC=$RPC_OK CRON=$CRON_OK JOBS=$CRON_JOBS"
fi
