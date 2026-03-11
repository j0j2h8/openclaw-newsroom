#!/usr/bin/env python3
"""
Morning Briefing Pipeline:
1. Python: Collect KOSPI200 + KOSDAQ150 + S&P500 + macro + news + Reddit (~45s)
2. OpenClaw Agent: 7-investor debate + stock picks → deliver to Slack
"""

import subprocess
import sys
from datetime import datetime

from market_data import collect_all, KST


# ─── Agent Prompts ───────────────────────────────────────────

COMMON_RULES = """## 규칙
- 한국어, 데이터 수치 정확 인용, 종목 날조 금지
- 상승/하락/거래량 상위 종목 데이터를 적극 활용하여 추천 근거 제시
- 각 대가의 어투/성격을 살려 생동감 있게
- 매크로 지표(환율, 유가, 금리 등)를 적극 활용한 분석
- 펀더멘탈 지표(PER, PBR, ROE, 부채비율, 매출/이익 성장률, 배당수익률 등)를 종목 추천 근거에 반드시 활용
- 버핏/그레이엄은 가치지표(PER, PBR, 배당), 린치는 성장지표(PEG, 이익성장), 우드는 매출성장, 달리오는 베타/상관관계를 각자 스타일에 맞게 인용
- 2500자 내외로 간결하게"""

PROMPTS = {
    "premarket": """당신은 전문 주식 시장 애널리스트이자 투자 대가 7인 토론 진행자입니다.
아래 수집된 실제 시장 데이터를 분석하여 *한국장 개장 전 프리마켓 브리핑*을 작성하세요.
미국 장 마감 결과, 야간 글로벌 흐름, 오늘 한국장에 미칠 영향을 중점 분석합니다.

## 출력 형식 (Slack mrkdwn, 코드블록/테이블 금지)

:sunrise: *프리마켓 브리핑* — {date}

*📋 핵심 요약*
오늘 한국장을 움직일 3대 요인

*🌍 글로벌 야간 동향*
• 미국 마감: 지수/섹터/특징적 종목 (🔴/🟢/🟡)
• 매크로: 원유/금/환율/채권 변동 & 한국장 영향
• 시간외/선물: 야간 흐름이 시사하는 오늘의 방향
• Reddit/커뮤니티: 해외 투자자 분위기

---

*🏛️ 투자 대가 위원회 — 오늘의 전략*

*📊 시장 진단*
🎩 버핏(가치투자): 1-2문장
📈 린치(GARP): 1-2문장
🌊 소로스(매크로): 1-2문장
⚖️ 달리오(올웨더): 1-2문장
📉 리버모어(모멘텀): 1-2문장
🛡️ 그레이엄(딥밸류): 1-2문장
🚀 우드(혁신): 1-2문장

*🔥 토론 하이라이트*
핵심 논쟁 2개를 대화체로 생생하게 — 오늘 매수/관망/매도 관점

*🇰🇷 한국 주목 3종목* (오늘 주시할 종목)
각 종목: *종목명* (전일종가, 등락률) — 오늘 주목 이유 / 리스크 / 전략

*🇺🇸 미국 주목 3종목* (시간외 흐름 반영)
같은 형식

*💡 오늘의 전략 한 줄*

_⚠️ AI 시뮬레이션이며 실제 투자 조언이 아닙니다._

""" + COMMON_RULES + """

## 수집 데이터

{data}""",

    "midday": """당신은 전문 주식 시장 애널리스트이자 투자 대가 7인 토론 진행자입니다.
아래 수집된 실제 시장 데이터를 분석하여 *장중 리포트*를 작성하세요.
한국장 전반 장세, 실시간 수급 변화, 후장 전략을 중점 분석합니다.

## 출력 형식 (Slack mrkdwn, 코드블록/테이블 금지)

:chart_with_upwards_trend: *장중 리포트* — {date}

*📋 전반 장세 요약*
오전장 핵심 3줄 요약

*📊 시장 현황*
• 한국: KOSPI/KOSDAQ 현재 수준, 등락 비율, 거래대금 특이점
• 섹터: 강세/약세 섹터 & 특징적 종목 이동
• 매크로 변동: 환율/유가/금리 실시간 변화 & 영향
• 수급: 외국인/기관/개인 매매 동향 (데이터 있으면)

---

*🏛️ 투자 대가 위원회 — 후장 전략*

*📊 시장 진단*
🎩 버핏(가치투자): 1-2문장
📈 린치(GARP): 1-2문장
🌊 소로스(매크로): 1-2문장
⚖️ 달리오(올웨더): 1-2문장
📉 리버모어(모멘텀): 1-2문장
🛡️ 그레이엄(딥밸류): 1-2문장
🚀 우드(혁신): 1-2문장

*🔥 토론 하이라이트*
핵심 논쟁 2개 — 후장 반등 가능성 vs 추가 하락, 매수 타이밍 논쟁

*🇰🇷 한국 후장 주목 3종목*
각 종목: *종목명* (현재가, 등락률) — 후장 관전포인트 / 리스크 / 전략

*🇺🇸 미국 프리마켓 감안 주목 3종목*
같은 형식

*💡 후장 전략 한 줄*

_⚠️ AI 시뮬레이션이며 실제 투자 조언이 아닙니다._

""" + COMMON_RULES + """

## 수집 데이터

{data}""",

    "closing": """당신은 전문 주식 시장 애널리스트이자 투자 대가 7인 토론 진행자입니다.
아래 수집된 실제 시장 데이터를 분석하여 *장마감 종합 분석*을 작성하세요.
한국장 마감 결과 총정리, 오늘의 승자/패자, 내일 전략을 중점 분석합니다.

## 출력 형식 (Slack mrkdwn, 코드블록/테이블 금지)

:city_sunset: *장마감 분석* — {date}

*📋 오늘의 시장 총평*
한 줄 총평 + 3대 이슈

*📊 마감 현황*
• 한국: KOSPI/KOSDAQ 마감 수치, 등락 비율, 거래대금
• 오늘의 승자/패자: 섹터별·종목별 최고/최저 성적표
• 매크로: 환율/유가/금리 종일 변동 요약
• 시장 통계: 상승/하락 비율, 거래량 특이점
• Reddit/글로벌: 해외 시장 분위기 & 오늘 밤 미국장 전망

---

*🏛️ 투자 대가 위원회 — 오늘의 리뷰 & 내일의 전략*

*📊 시장 진단*
🎩 버핏(가치투자): 1-2문장
📈 린치(GARP): 1-2문장
🌊 소로스(매크로): 1-2문장
⚖️ 달리오(올웨더): 1-2문장
📉 리버모어(모멘텀): 1-2문장
🛡️ 그레이엄(딥밸류): 1-2문장
🚀 우드(혁신): 1-2문장

*🔥 토론 하이라이트*
핵심 논쟁 2개 — 오늘 복기 & 내일 포지션 논쟁

*🇰🇷 한국 내일 주목 3종목*
각 종목: *종목명* (마감가, 등락률, 펀더멘탈) — 내일 전략 / 리스크 / 목표수익률·손절

*🇺🇸 미국 오늘 밤 주목 3종목*
같은 형식

*💡 내일을 위한 한 줄*

_⚠️ AI 시뮬레이션이며 실제 투자 조언이 아닙니다._

""" + COMMON_RULES + """

## 수집 데이터

{data}""",
}


# ─── Agent Call + Delivery ───────────────────────────────────

BRIEFING_TYPES = {
    "premarket": "프리마켓 브리핑",
    "midday": "장중 리포트",
    "closing": "장마감 분석",
}


def run_agent(data: str, briefing_type: str = "premarket") -> str:
    now = datetime.now(KST)
    template = PROMPTS.get(briefing_type, PROMPTS["premarket"])
    prompt = template.format(
        date=now.strftime("%Y-%m-%d (%a)"),
        data=data,
    )

    result = subprocess.run(
        [
            "openclaw", "agent",
            "--agent", "main",
            "--deliver",
            "--reply-channel", "slack",
            "--reply-to", "C0AE3P4JNR1",
            "--message", prompt,
            "--thinking", "medium",
            "--timeout", "600",
        ],
        capture_output=True, text=True, timeout=660,
    )

    if result.returncode != 0:
        print(f"Agent error: {result.stderr[:500]}", file=sys.stderr)
    return result.stdout.strip()


# ─── Main ────────────────────────────────────────────────────

def main():
    briefing_type = sys.argv[1] if len(sys.argv) > 1 else "premarket"
    if briefing_type not in BRIEFING_TYPES:
        print(f"Usage: {sys.argv[0]} [premarket|midday|closing]", file=sys.stderr)
        sys.exit(1)

    label = BRIEFING_TYPES[briefing_type]
    log = lambda msg: print(f"[{datetime.now(KST).isoformat()}] {msg}")

    log(f"=== {label} Pipeline ===")
    log("Step 1/2: Collecting market data (KOSPI200 + KOSDAQ150 + S&P500 + macro)...")

    data = collect_all()
    log(f"Collected {len(data)} chars")

    log(f"Step 2/2: Agent analyzing ({label}) + delivering to Slack...")
    output = run_agent(data, briefing_type)
    log(f"Agent done ({len(output)} chars)")

    if output:
        log("=== Delivered to Slack ===")
    else:
        log("=== WARNING: No agent output ===")


if __name__ == "__main__":
    main()
