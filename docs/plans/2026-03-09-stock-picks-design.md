# Stock Picks Multi-Agent System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 4명의 OpenClaw 에이전트(researcher, analyst, risk-manager, reporter)가 순차적으로 협업하여 종목추천을 생성하고 Slack #ai-picks로 전송하는 시스템 구축

**Architecture:** Python 오케스트레이터(`stock-picks.py`)가 데이터 수집 후 4개 에이전트를 순차 호출. 각 에이전트는 독립 workspace와 IDENTITY/SOUL을 갖고, 중간 결과를 JSON 파일로 전달. 기존 `morning-briefing.py`의 데이터 수집 코드를 공통 모듈로 분리하여 재활용.

**Tech Stack:** Python 3.9, OpenClaw CLI (`openclaw agent`), yfinance, Yahoo Finance v8 API, Slack via OpenClaw delivery

---

## Task 1: 데이터 수집 코드를 공통 모듈로 분리

**Files:**
- Create: `~/.openclaw/workspace/scripts/market_data.py`
- Modify: `~/.openclaw/workspace/scripts/morning-briefing.py`

**Step 1: `market_data.py` 생성**

`morning-briefing.py`에서 데이터 수집 관련 코드를 추출하여 독립 모듈로 분리:
- 상수: `INDICES`, `SECTOR_ETFS`, `MACRO_SYMBOLS`, `NEWS_FEEDS`, `REDDIT_SUBS`, `TOP_N`, `KST`, `UA`, `DATA_DIR`
- 함수: `load_ticker_list()`, `fetch_url()`, `fetch_quote()`, `fetch_quotes_parallel()`, `fetch_rss()`, `fetch_reddit()`, `fmt_pct()`, `format_stock_line()`, `top_bottom()`, `fetch_fundamentals_batch()`, `fmt_fund()`, `collect_all()`

```python
# ~/.openclaw/workspace/scripts/market_data.py
"""공통 시장 데이터 수집 모듈 — morning-briefing.py, stock-picks.py에서 공유"""
# (morning-briefing.py에서 데이터 수집 관련 코드 전체를 이동)
```

**Step 2: `morning-briefing.py` 수정**

데이터 수집 코드를 `market_data`에서 import하도록 변경:

```python
from market_data import collect_all, KST
```

프롬프트 템플릿과 에이전트 호출/main 함수만 남김.

**Step 3: 기존 브리핑 동작 확인**

Run: `/usr/bin/python3 ~/.openclaw/workspace/scripts/morning-briefing.py closing 2>&1 | head -5`
Expected: `=== 장마감 분석 Pipeline ===` 정상 출력

**Step 4: Commit**

```bash
git add scripts/market_data.py scripts/morning-briefing.py
git commit -m "refactor: extract market data collection into shared module"
```

---

## Task 2: Slack #ai-picks 채널 등록

**Files:**
- Modify: `~/.openclaw/openclaw.json`

**Step 1: openclaw.json에 #ai-picks 채널 추가**

```json
"channels": {
  "#ai-bot": { "allow": true },
  "#ai-briefing": { "allow": true },
  "#ai-picks": { "allow": true }
}
```

**Step 2: 채널 ID 확인**

사용자에게 Slack에서 #ai-picks 채널 생성 후 채널 ID를 요청.
또는 `openclaw channels resolve --channel slack "ai-picks"` 시도.

**Step 3: 테스트 메시지 전송**

```bash
openclaw agent --agent main --deliver --reply-channel slack --reply-to "<CHANNEL_ID>" \
  --message "🧪 #ai-picks 채널 연동 테스트" --thinking off --timeout 30
```

Expected: Slack #ai-picks에 테스트 메시지 도착

---

## Task 3: 4개 에이전트 생성 (researcher, analyst, risk-manager, reporter)

**Files:**
- Create: `~/.openclaw/agents/researcher/workspace/IDENTITY.md`
- Create: `~/.openclaw/agents/researcher/workspace/SOUL.md`
- Create: `~/.openclaw/agents/analyst/workspace/IDENTITY.md`
- Create: `~/.openclaw/agents/analyst/workspace/SOUL.md`
- Create: `~/.openclaw/agents/risk-manager/workspace/IDENTITY.md`
- Create: `~/.openclaw/agents/risk-manager/workspace/SOUL.md`
- Create: `~/.openclaw/agents/reporter/workspace/IDENTITY.md`
- Create: `~/.openclaw/agents/reporter/workspace/SOUL.md`

**Step 1: researcher 에이전트 생성**

```bash
openclaw agents add researcher \
  --workspace ~/.openclaw/agents/researcher/workspace \
  --model openai-codex/gpt-5.4 \
  --non-interactive
```

IDENTITY.md:
```markdown
# IDENTITY
- Name: Researcher
- Role: 시장 리서처
- Emoji: 🔍
- Vibe: 꼼꼼하고 데이터 중심적, 팩트만 전달
```

SOUL.md:
```markdown
# SOUL

당신은 주식 시장 리서처입니다.

## 핵심 원칙
- 수집된 원시 데이터에서 투자에 유의미한 신호를 추출합니다
- 뉴스, 매크로, 섹터 동향, 펀더멘탈, 수급 이상을 분석합니다
- 주관적 의견 없이 팩트와 데이터 기반으로만 보고합니다
- 한국(KOSPI200+KOSDAQ150)과 미국(S&P500)에서 각각 주목 종목 10개를 선별합니다

## 출력 형식
반드시 유효한 JSON으로 출력합니다. 다른 텍스트 없이 JSON만 출력합니다.

```json
{
  "date": "YYYY-MM-DD",
  "type": "premarket|closing",
  "macro_summary": "매크로 환경 요약 (3줄)",
  "market_regime": "risk-on|risk-off|mixed",
  "sector_signals": [
    {"sector": "섹터명", "signal": "strong|neutral|weak", "reason": "근거"}
  ],
  "watchlist_kr": [
    {
      "symbol": "005930.KS",
      "name": "삼성전자",
      "reason": "주목 이유",
      "catalyst": "촉매 요인",
      "news": ["관련 뉴스 제목"],
      "fundamentals": {"PER": 6.4, "ROE": 10.8, ...}
    }
  ],
  "watchlist_us": [
    {
      "symbol": "NVDA",
      "name": "NVIDIA",
      "reason": "주목 이유",
      "catalyst": "촉매 요인",
      "news": ["관련 뉴스 제목"],
      "fundamentals": {"PER": 36.2, "ROE": 101.5, ...}
    }
  ],
  "risk_factors": ["리스크 요인 1", "리스크 요인 2"]
}
```
```

**Step 2: analyst 에이전트 생성**

```bash
openclaw agents add analyst \
  --workspace ~/.openclaw/agents/analyst/workspace \
  --model openai-codex/gpt-5.4 \
  --non-interactive
```

IDENTITY.md:
```markdown
# IDENTITY
- Name: Analyst
- Role: 기술적 애널리스트
- Emoji: 📊
- Vibe: 분석적이고 정량적, 점수와 등급으로 판단
```

SOUL.md:
```markdown
# SOUL

당신은 주식 기술적 애널리스트입니다.

## 핵심 원칙
- researcher가 선별한 종목을 기술적+펀더멘탈 관점에서 점수화합니다
- 각 종목에 0~100 종합점수를 부여합니다
- 점수 기준: 모멘텀(20), 밸류에이션(20), 성장성(20), 수급(20), 촉매(20)
- 점수 70 이상: 매수, 50~69: 관망, 50 미만: 회피

## 출력 형식
반드시 유효한 JSON으로 출력합니다. 다른 텍스트 없이 JSON만 출력합니다.

```json
{
  "date": "YYYY-MM-DD",
  "type": "premarket|closing",
  "scored_kr": [
    {
      "symbol": "005930.KS",
      "name": "삼성전자",
      "score": 78,
      "grade": "매수",
      "breakdown": {
        "momentum": 15,
        "valuation": 18,
        "growth": 16,
        "flow": 14,
        "catalyst": 15
      },
      "technical": "5일 추세, 52주 대비 위치, 거래량 분석",
      "entry_price": 170000,
      "target_price": 195000,
      "rationale": "종합 판단 근거"
    }
  ],
  "scored_us": [
    {
      "symbol": "NVDA",
      "name": "NVIDIA",
      "score": 72,
      "grade": "매수",
      "breakdown": { ... },
      "technical": "...",
      "entry_price": 175.0,
      "target_price": 195.0,
      "rationale": "..."
    }
  ]
}
```
```

**Step 3: risk-manager 에이전트 생성**

```bash
openclaw agents add risk-manager \
  --workspace ~/.openclaw/agents/risk-manager/workspace \
  --model openai-codex/gpt-5.4 \
  --non-interactive
```

IDENTITY.md:
```markdown
# IDENTITY
- Name: Risk Manager
- Role: 리스크 매니저
- Emoji: 🛡️
- Vibe: 보수적이고 신중, 손실 방지가 최우선
```

SOUL.md:
```markdown
# SOUL

당신은 주식 포트폴리오 리스크 매니저입니다.

## 핵심 원칙
- analyst의 점수화 결과를 리스크 관점에서 필터링합니다
- 한국 3종목, 미국 3종목을 최종 선정합니다
- 각 종목에 포지션 비중(%), 손절선, 목표가를 설정합니다
- 진입 차단 조건: 변동성 과다(β>2.5), 유동성 부족, 과매수 구간, 섹터 집중 리스크
- 포트폴리오 전체 리스크도 평가합니다

## 출력 형식
반드시 유효한 JSON으로 출력합니다. 다른 텍스트 없이 JSON만 출력합니다.

```json
{
  "date": "YYYY-MM-DD",
  "type": "premarket|closing",
  "market_risk": "low|medium|high|extreme",
  "portfolio_beta": 1.25,
  "picks_kr": [
    {
      "symbol": "005930.KS",
      "name": "삼성전자",
      "score": 78,
      "weight_pct": 35,
      "entry_price": 170000,
      "stop_loss": 161500,
      "stop_loss_pct": -5.0,
      "target_price": 195000,
      "target_pct": 14.7,
      "risk_reward": 2.94,
      "holding_period": "1~2주",
      "risks": ["반도체 추가 조정", "환율 부담"]
    }
  ],
  "picks_us": [ ... ],
  "blocked": [
    {"symbol": "XXX", "reason": "차단 사유"}
  ],
  "portfolio_notes": "포트폴리오 전체 코멘트"
}
```
```

**Step 4: reporter 에이전트 생성**

```bash
openclaw agents add reporter \
  --workspace ~/.openclaw/agents/reporter/workspace \
  --model openai-codex/gpt-5.4 \
  --non-interactive
```

IDENTITY.md:
```markdown
# IDENTITY
- Name: Reporter
- Role: 투자 리포터
- Emoji: 📝
- Vibe: 명확하고 읽기 쉬운, 핵심만 전달
```

SOUL.md:
```markdown
# SOUL

당신은 투자 리포트 작성 전문가입니다.

## 핵심 원칙
- risk-manager의 최종 추천 결과를 Slack 보고서로 변환합니다
- Slack mrkdwn 형식, 코드블록/테이블 금지
- 간결하고 실행 가능한 정보 위주
- 데이터 수치를 정확히 인용

## 출력 형식 (Slack mrkdwn)

:dart: *종목추천 리포트* — {date} ({type})

*📋 시장 환경*
• 시장 리스크: {market_risk} | 포트폴리오 β: {portfolio_beta}
• 매크로 요약 1줄

---

*🇰🇷 한국 추천 3종목*
각 종목:
*{name}* ({symbol}) — 점수: {score}/100 | 비중: {weight}%
• 진입: {entry} → 목표: {target} ({target_pct}) | 손절: {stop} ({stop_pct})
• R/R: {risk_reward} | 보유: {holding}
• 근거: {rationale}
• 리스크: {risks}

*🇺🇸 미국 추천 3종목*
같은 형식

*🚫 진입 차단 종목*
차단된 종목과 사유

*⚠️ 포트폴리오 노트*
{portfolio_notes}

_AI 시뮬레이션이며 실제 투자 조언이 아닙니다._
```

**Step 5: 에이전트 등록 확인**

Run: `openclaw agents list`
Expected: main, researcher, analyst, risk-manager, reporter 5개 에이전트 표시

---

## Task 4: 오케스트레이터 스크립트 작성

**Files:**
- Create: `~/.openclaw/workspace/scripts/stock-picks.py`

**Step 1: stock-picks.py 작성**

```python
#!/usr/bin/env python3
"""
Stock Picks Pipeline:
1. Python: Collect market data (shared module)
2. researcher: 뉴스/공시/시장 데이터 조사 → researcher.json
3. analyst: 기술적 분석, 종목 점수화 → analyst.json
4. risk-manager: 손절, 비중, 진입 차단 → risk-manager.json
5. reporter: Slack 보고서 작성 → #ai-picks 전송
"""

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from market_data import collect_all, KST

DATA_DIR = Path("/Users/j/.openclaw/workspace/data/picks")
SLACK_CHANNEL_ID = "<AI_PICKS_CHANNEL_ID>"  # #ai-picks 채널 ID

AGENTS = ["researcher", "analyst", "risk-manager", "reporter"]


def today_dir(briefing_type: str) -> Path:
    now = datetime.now(KST)
    d = DATA_DIR / now.strftime("%Y-%m-%d") / briefing_type
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_agent(agent: str, message: str, deliver: bool = False) -> str:
    cmd = [
        "openclaw", "agent",
        "--agent", agent,
        "--message", message,
        "--thinking", "medium",
        "--timeout", "600",
    ]
    if deliver:
        cmd += ["--deliver", "--reply-channel", "slack", "--reply-to", SLACK_CHANNEL_ID]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=660)
    if result.returncode != 0:
        print(f"[{agent}] error: {result.stderr[:500]}", file=sys.stderr)
    return result.stdout.strip()


def main():
    briefing_type = sys.argv[1] if len(sys.argv) > 1 else "closing"
    if briefing_type not in ("premarket", "closing"):
        print(f"Usage: {sys.argv[0]} [premarket|closing]", file=sys.stderr)
        sys.exit(1)

    log = lambda msg: print(f"[{datetime.now(KST).isoformat()}] {msg}")
    out_dir = today_dir(briefing_type)

    # Step 1: Collect data
    log("Step 1/5: Collecting market data...")
    raw_data = collect_all()
    (out_dir / "raw-data.txt").write_text(raw_data)
    log(f"Collected {len(raw_data)} chars")

    # Step 2: Researcher
    log("Step 2/5: Researcher analyzing...")
    researcher_prompt = f"""아래 시장 데이터를 분석하여 주목 종목을 선별하세요.
브리핑 타입: {briefing_type}

{raw_data}"""
    researcher_out = run_agent("researcher", researcher_prompt)
    (out_dir / "researcher.json").write_text(researcher_out)
    log(f"Researcher done ({len(researcher_out)} chars)")

    # Step 3: Analyst
    log("Step 3/5: Analyst scoring...")
    analyst_prompt = f"""아래 researcher 분석 결과와 원시 데이터를 기반으로 종목을 점수화하세요.
브리핑 타입: {briefing_type}

## Researcher 결과
{researcher_out}

## 원시 시장 데이터
{raw_data}"""
    analyst_out = run_agent("analyst", analyst_prompt)
    (out_dir / "analyst.json").write_text(analyst_out)
    log(f"Analyst done ({len(analyst_out)} chars)")

    # Step 4: Risk Manager
    log("Step 4/5: Risk Manager filtering...")
    risk_prompt = f"""아래 analyst 점수화 결과를 리스크 관점에서 필터링하고 최종 추천을 확정하세요.
브리핑 타입: {briefing_type}

## Analyst 결과
{analyst_out}"""
    risk_out = run_agent("risk-manager", risk_prompt)
    (out_dir / "risk-manager.json").write_text(risk_out)
    log(f"Risk Manager done ({len(risk_out)} chars)")

    # Step 5: Reporter
    log("Step 5/5: Reporter writing & delivering...")
    reporter_prompt = f"""아래 최종 추천 결과를 Slack 보고서로 작성하세요.
브리핑 타입: {briefing_type}
날짜: {datetime.now(KST).strftime('%Y-%m-%d (%a)')}

## Risk Manager 최종 결과
{risk_out}"""
    reporter_out = run_agent("reporter", reporter_prompt, deliver=True)
    (out_dir / "report.md").write_text(reporter_out)
    log(f"Reporter done ({len(reporter_out)} chars)")

    log("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
```

**Step 2: 실행 테스트**

Run: `/usr/bin/python3 ~/.openclaw/workspace/scripts/stock-picks.py closing`
Expected: 5단계 순차 실행, `data/picks/YYYY-MM-DD/closing/` 디렉토리에 파일 생성, Slack #ai-picks 전송

**Step 3: Commit**

```bash
git add scripts/stock-picks.py
git commit -m "feat: add multi-agent stock picks pipeline"
```

---

## Task 5: 크론탭 등록

**Step 1: crontab 업데이트**

기존 브리핑 크론에 추가:

```crontab
# 종목추천 → Slack #ai-picks (월~금)
# 07:00 프리마켓 추천
0 7 * * 1-5 /usr/bin/python3 /Users/j/.openclaw/workspace/scripts/stock-picks.py premarket >> /Users/j/.openclaw/logs/stock-picks.log 2>&1
# 18:30 장마감 추천
30 18 * * 1-5 /usr/bin/python3 /Users/j/.openclaw/workspace/scripts/stock-picks.py closing >> /Users/j/.openclaw/logs/stock-picks.log 2>&1
```

**Step 2: 확인**

Run: `crontab -l`
Expected: 브리핑 3개 + 종목추천 2개 = 5개 크론 항목

---

## 실행 순서 요약

| 순서 | Task | 예상 시간 |
|------|------|----------|
| 1 | 데이터 수집 모듈 분리 | 5분 |
| 2 | Slack #ai-picks 채널 등록 | 2분 (채널 ID 필요) |
| 3 | 4개 에이전트 생성 | 10분 |
| 4 | 오케스트레이터 스크립트 | 5분 |
| 5 | 크론탭 등록 | 2분 |
