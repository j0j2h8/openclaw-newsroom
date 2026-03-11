#!/usr/bin/env python3
"""
Stock Picks Pipeline:
1. Python: Collect market data (shared module)
2. researcher: 뉴스/공시/시장 데이터 조사 → researcher.json
3. tech/fundamental/news-analyst (병렬): 각 관점 분석
4. chief-analyst: 3명 결과 취합 → chief-analyst.json
5. risk-manager: 손절, 비중, 진입 차단 → risk-manager.json
6. reporter: Slack 보고서 작성 → #ai-picks 전송
"""

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from market_data import collect_all, KST


def extract_watchlist_data(researcher_json: str, raw_data: str) -> str:
    """Extract raw data lines only for watchlist symbols from researcher output."""
    try:
        research = json.loads(researcher_json)
    except json.JSONDecodeError:
        return raw_data  # fallback to full data

    symbols = set()
    for item in research.get("watchlist_kr", []):
        symbols.add(item["symbol"])
    for item in research.get("watchlist_us", []):
        symbols.add(item["symbol"])

    if not symbols:
        return raw_data

    # Keep macro/index/sector/summary/news/reddit sections + only matching stock lines
    filtered_lines = []
    in_stock_section = False
    include_line = False
    for line in raw_data.split("\n"):
        # Detect stock listing sections
        if line.startswith("## KOSPI") or line.startswith("## KOSDAQ") or line.startswith("## S&P"):
            in_stock_section = True
            filtered_lines.append(line)
            continue
        if line.startswith("## ") and in_stock_section:
            in_stock_section = False

        if in_stock_section:
            if line.startswith("- "):
                # Check if this stock line matches a watchlist symbol
                include_line = any(f"({sym})" in line for sym in symbols)
            elif line.startswith("    ["):
                pass  # fundamentals line follows previous stock line
            else:
                include_line = False
            if include_line:
                filtered_lines.append(line)
        else:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)

DATA_DIR = Path("/Users/j/.openclaw/workspace/data/picks")
SLACK_CHANNEL_ID = "C0AKAV7QD0W"  # #ai-picks


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
        raise RuntimeError(f"[{agent}] failed (exit {result.returncode}): {result.stderr[:500]}")
    output = result.stdout.strip()
    if not output:
        raise RuntimeError(f"[{agent}] returned empty output")
    return output


def main():
    briefing_type = sys.argv[1] if len(sys.argv) > 1 else "closing"
    if briefing_type not in ("premarket", "closing"):
        print(f"Usage: {sys.argv[0]} [premarket|closing]", file=sys.stderr)
        sys.exit(1)

    log = lambda msg: print(f"[{datetime.now(KST).isoformat()}] {msg}")
    out_dir = today_dir(briefing_type)

    # Step 1: Collect data
    log("Step 1/6: Collecting market data...")
    raw_data = collect_all(top_n=0)
    (out_dir / "raw-data.txt").write_text(raw_data)
    log(f"Collected {len(raw_data)} chars")

    # Step 2: Researcher
    log("Step 2/6: Researcher analyzing...")
    researcher_prompt = f"""아래 시장 데이터를 분석하여 주목 종목을 선별하세요.
브리핑 타입: {briefing_type}

{raw_data}"""
    researcher_out = run_agent("researcher", researcher_prompt)
    (out_dir / "researcher.json").write_text(researcher_out)
    log(f"Researcher done ({len(researcher_out)} chars)")

    # Step 3: 3 sub-analysts in parallel
    log("Step 3/6: Sub-analysts analyzing in parallel (tech / fundamental / news)...")

    watchlist_data = extract_watchlist_data(researcher_out, raw_data)
    log(f"Watchlist data: {len(watchlist_data)} chars (filtered from {len(raw_data)})")

    common_context = f"""브리핑 타입: {briefing_type}

## Researcher 결과
{researcher_out}

## 워치리스트 종목 시장 데이터
{watchlist_data}"""

    sub_analysts = {
        "tech-analyst": f"아래 researcher가 선별한 종목들의 기술적 분석(차트, 추세, 거래량, 모멘텀)을 수행하세요.\n\n{common_context}",
        "fundamental-analyst": f"아래 researcher가 선별한 종목들의 펀더멘탈 분석(PER, PBR, ROE, 성장성, 배당)을 수행하세요.\n\n{common_context}",
        "news-analyst": f"아래 researcher가 선별한 종목들의 뉴스/촉매 분석(뉴스, 이벤트, 섹터 테마, 감성)을 수행하세요.\n\n{common_context}",
    }

    sub_results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(run_agent, name, prompt): name for name, prompt in sub_analysts.items()}
        for future in futures:
            name = futures[future]
            result = future.result()
            sub_results[name] = result
            (out_dir / f"{name}.json").write_text(result)
            log(f"  {name} done ({len(result)} chars)")

    # Step 4: Chief Analyst — synthesize
    log("Step 4/6: Chief Analyst synthesizing...")
    chief_prompt = f"""3명의 전문 분석가 결과를 취합하여 종합 점수를 산출하세요.
브리핑 타입: {briefing_type}

## Tech Analyst 결과 (차트/모멘텀/수급)
{sub_results['tech-analyst']}

## Fundamental Analyst 결과 (밸류에이션/성장성)
{sub_results['fundamental-analyst']}

## News Analyst 결과 (뉴스/촉매)
{sub_results['news-analyst']}

## Researcher 원본 (참고용)
{researcher_out}

## 현재가 참조 (current_price 설정 시 반드시 이 데이터 사용)
{watchlist_data}"""
    chief_out = run_agent("chief-analyst", chief_prompt)
    (out_dir / "chief-analyst.json").write_text(chief_out)
    log(f"Chief Analyst done ({len(chief_out)} chars)")

    # Step 5: Risk Manager
    log("Step 5/6: Risk Manager filtering...")
    risk_prompt = f"""아래 chief-analyst 점수화 결과를 리스크 관점에서 필터링하고 최종 추천을 확정하세요.
브리핑 타입: {briefing_type}

## Chief Analyst 결과
{chief_out}

## 현재가 참조 (가격 정합성 검증 시 반드시 이 데이터와 대조)
{watchlist_data}"""
    risk_out = run_agent("risk-manager", risk_prompt)
    (out_dir / "risk-manager.json").write_text(risk_out)
    log(f"Risk Manager done ({len(risk_out)} chars)")

    # Step 6: Reporter
    log("Step 6/6: Reporter writing & delivering...")
    reporter_prompt = f"""아래 최종 추천 결과를 Slack 보고서로 작성하세요.
브리핑 타입: {briefing_type}
날짜: {datetime.now(KST).strftime('%Y-%m-%d (%a)')}

## Risk Manager 최종 결과
{risk_out}

## Chief Analyst 분석 (chief 요약 작성 시 이 데이터의 rationale, conflicts 인용)
{chief_out}"""
    reporter_out = run_agent("reporter", reporter_prompt, deliver=True)
    (out_dir / "report.md").write_text(reporter_out)
    log(f"Reporter done ({len(reporter_out)} chars)")

    log("=== Pipeline complete (6 steps) ===")


if __name__ == "__main__":
    main()
