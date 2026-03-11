"""Market data collection module for morning briefing pipeline.

Collects KOSPI200, KOSDAQ150, S&P500 quotes, macro indicators,
news feeds, and Reddit sentiment data.
"""

import json
import statistics
import sys
import urllib.request
import warnings
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
DATA_DIR = Path("/Users/j/.openclaw/workspace/data")

# ─── Config ──────────────────────────────────────────────────

INDICES = {
    "KOSPI": "^KS11", "KOSDAQ": "^KQ11",
    "S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI",
    "Russell 2000": "^RUT", "VIX": "^VIX",
}

SECTOR_ETFS = {
    "기술": "XLK", "금융": "XLF", "에너지": "XLE",
    "헬스케어": "XLV", "산업재": "XLI", "커뮤니케이션": "XLC",
    "부동산": "XLRE", "반도체": "SMH", "혁신": "ARKK",
    "경기소비재": "XLY", "필수소비재": "XLP", "유틸리티": "XLU",
}

MACRO_SYMBOLS = {
    "WTI 원유": "CL=F", "브렌트유": "BZ=F", "천연가스": "NG=F",
    "금": "GC=F", "은": "SI=F", "구리": "HG=F",
    "USD/KRW": "KRW=X", "USD/JPY": "JPY=X", "EUR/USD": "EURUSD=X",
    "달러인덱스": "DX-Y.NYB",
    "미국10년국채": "^TNX", "미국2년국채": "^IRX",
    "비트코인": "BTC-USD",
}

NEWS_FEEDS = {
    "글로벌 매크로": [
        "https://news.google.com/rss/search?q=global+economy+fed+inflation+rate&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=geopolitics+trade+tariff+sanctions+oil&hl=en-US&gl=US&ceid=US:en",
    ],
    "미국 시장": [
        "https://news.google.com/rss/search?q=wall+street+S%26P+NASDAQ+earnings&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=US+stock+market+fed+rate+economy&hl=en-US&gl=US&ceid=US:en",
    ],
    "한국 시장": [
        "https://news.google.com/rss/search?q=%EC%BD%94%EC%8A%A4%ED%94%BC+%EC%BD%94%EC%8A%A4%EB%8B%A5+%EC%A6%9D%EC%8B%9C&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=%ED%95%9C%EA%B5%AD+%EC%A3%BC%EC%8B%9D+%EC%8B%9C%EC%9E%A5+%EA%B2%BD%EC%A0%9C&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "원자재/에너지": [
        "https://news.google.com/rss/search?q=crude+oil+price+OPEC+energy&hl=en-US&gl=US&ceid=US:en",
    ],
}

REDDIT_SUBS = [("wallstreetbets", 10), ("stocks", 8), ("investing", 5)]

TOP_N = 15  # top/bottom movers to include in output

FUND_KEYS = [
    "marketCap", "trailingPE", "forwardPE", "priceToBook",
    "returnOnEquity", "returnOnAssets", "debtToEquity",
    "revenueGrowth", "earningsGrowth", "profitMargins",
    "dividendYield", "beta", "trailingEps", "forwardEps",
]


# ─── Ticker Lists ────────────────────────────────────────────

def load_ticker_list(filename, ticker_key="tickers", name_key="names"):
    path = DATA_DIR / filename
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        tickers = data if isinstance(data, list) else data.get(ticker_key, [])
        names = data.get(name_key, {}) if isinstance(data, dict) else {}
        return tickers, names
    return [], {}


# ─── Data Collection ─────────────────────────────────────────

def fetch_url(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_quote(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d"
    try:
        data = json.loads(fetch_url(url))
        r = data["chart"]["result"][0]
        meta = r["meta"]
        price = meta["regularMarketPrice"]
        closes = [c for c in r["indicators"]["quote"][0].get("close", []) if c is not None]
        prev = closes[-2] if len(closes) >= 2 else meta.get("chartPreviousClose", 0)
        chg = ((price - prev) / prev * 100) if prev else 0
        vols = [v for v in r["indicators"]["quote"][0].get("volume", []) if v is not None]

        # Moving averages
        ma5 = round(sum(closes[-5:]) / len(closes[-5:]), 2) if len(closes) >= 5 else None
        ma20 = round(sum(closes[-20:]) / len(closes[-20:]), 2) if len(closes) >= 20 else None
        ma60 = round(sum(closes[-60:]) / len(closes[-60:]), 2) if len(closes) >= 60 else None

        # Bollinger Bands (20-day)
        bb_upper, bb_lower = None, None
        if len(closes) >= 20:
            std20 = statistics.stdev(closes[-20:])
            bb_upper = round(ma20 + 2 * std20, 2)
            bb_lower = round(ma20 - 2 * std20, 2)

        # RSI (14-day): closes[-1]이 당일 가격이므로 closes를 그대로 사용
        rsi = None
        if len(closes) >= 15:
            deltas = [closes[i] - closes[i-1] for i in range(-14, 0)]
            gains = [d for d in deltas if d > 0]
            losses = [-d for d in deltas if d < 0]
            avg_gain = sum(gains) / 14 if gains else 0
            avg_loss = sum(losses) / 14 if losses else 0
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = round(100 - (100 / (1 + rs)), 1)
            elif avg_gain > 0:
                rsi = 100.0
            else:
                rsi = 50.0

        return {
            "symbol": symbol,
            "name": meta.get("longName", meta.get("shortName", symbol)),
            "price": round(price, 2),
            "prev_close": round(prev, 2),
            "change_pct": round(chg, 2),
            "volume": vols[-1] if vols else 0,
            "volumes_5d": [v for v in vols[-5:]],
            "day_high": round(meta["regularMarketDayHigh"], 2) if meta.get("regularMarketDayHigh") else None,
            "day_low": round(meta["regularMarketDayLow"], 2) if meta.get("regularMarketDayLow") else None,
            "week52_high": round(meta["fiftyTwoWeekHigh"], 2) if meta.get("fiftyTwoWeekHigh") else None,
            "week52_low": round(meta["fiftyTwoWeekLow"], 2) if meta.get("fiftyTwoWeekLow") else None,
            "closes_5d": [round(c, 2) for c in closes[-5:]],
            "closes_20d": [round(c, 2) for c in closes[-20:]],
            "ma5": ma5,
            "ma20": ma20,
            "ma60": ma60,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "rsi": rsi,
        }
    except Exception as e:
        print(f"[WARN] fetch_quote({symbol}) failed: {e}", file=sys.stderr)
        return None


def fetch_quotes_parallel(symbols, max_workers=20):
    results = []
    failed = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_quote, s): s for s in symbols}
        for f in as_completed(futures):
            sym = futures[f]
            q = f.result()
            if q:
                results.append(q)
            else:
                failed.append(sym)
    if failed:
        print(f"[WARN] {len(failed)} symbols failed: {', '.join(failed[:10])}", file=sys.stderr)
    return results


def _parse_rss_date(date_str):
    """Parse RFC 2822 date string, return datetime or None."""
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def fetch_rss(url, max_items=5, max_age_days=7):
    try:
        tree = ET.fromstring(fetch_url(url))
    except Exception:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    items = []
    for item in tree.iter("item"):
        title = (item.findtext("title") or "").strip()
        source = (item.findtext("source") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if not title:
            continue
        pub_dt = _parse_rss_date(pub) if pub else None
        if pub_dt and pub_dt < cutoff:
            continue
        items.append({"title": title, "source": source, "date": pub})
        if len(items) >= max_items:
            break
    return items


def fetch_reddit(sub, limit):
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
    try:
        data = json.loads(fetch_url(url))
        return [
            {
                "title": d.get("title", ""),
                "score": d.get("score", 0),
                "comments": d.get("num_comments", 0),
                "upvote_ratio": d.get("upvote_ratio", 0),
                "flair": d.get("link_flair_text", ""),
            }
            for child in data.get("data", {}).get("children", [])
            if not (d := child.get("data", {})).get("stickied")
        ]
    except Exception:
        return []


# ─── Format ──────────────────────────────────────────────────

def fmt_pct(v):
    return f"{v:+.2f}%"


def format_stock_line(q, name_map, currency="", fund_map=None):
    display_name = name_map.get(q["symbol"], q["name"])
    w52 = ""
    if q.get("week52_high") and q.get("week52_low"):
        w52 = f"  52주:{q['week52_low']:,}~{q['week52_high']:,}"
    day = ""
    if q.get("day_high") and q.get("day_low"):
        if currency == "KRW":
            day = f"  당일:{q['day_low']:,.0f}~{q['day_high']:,.0f}"
        else:
            day = f"  당일:{q['day_low']:.2f}~{q['day_high']:.2f}"
    trend = ""
    if q.get("closes_5d") and len(q["closes_5d"]) >= 2:
        if currency == "KRW":
            trend = f"  [5일: {' → '.join(f'{c:,.0f}' for c in q['closes_5d'])}]"
        else:
            trend = f"  [5일: {' → '.join(str(c) for c in q['closes_5d'])}]"
    # Technical indicators
    tech = ""
    parts = []
    if q.get("ma5") is not None:
        parts.append(f"MA5:{q['ma5']:,.2f}")
    if q.get("ma20") is not None:
        parts.append(f"MA20:{q['ma20']:,.2f}")
    if q.get("ma60") is not None:
        parts.append(f"MA60:{q['ma60']:,.2f}")
    if q.get("bb_upper") is not None and q.get("bb_lower") is not None:
        parts.append(f"BB:{q['bb_lower']:,.2f}~{q['bb_upper']:,.2f}")
    if q.get("rsi") is not None:
        parts.append(f"RSI:{q['rsi']}")
    if q.get("volumes_5d") and len(q["volumes_5d"]) >= 2:
        avg_vol = sum(q["volumes_5d"][:-1]) / len(q["volumes_5d"][:-1])
        if avg_vol > 0:
            vol_ratio = q["volumes_5d"][-1] / avg_vol
            parts.append(f"거래량비:{vol_ratio:.1f}x")
    if parts:
        tech = f"\n    [{' | '.join(parts)}]"

    fund_str = ""
    if fund_map and q["symbol"] in fund_map:
        fund_str = f"\n    [{fmt_fund(fund_map[q['symbol']], currency)}]"
    if currency == "KRW":
        return f"- {display_name} ({q['symbol']}): {q['price']:,.0f}원 ({fmt_pct(q['change_pct'])}) 전일:{q['prev_close']:,.0f} 거래량:{q['volume']:,}{w52}{day}{trend}{tech}{fund_str}"
    else:
        return f"- {q['name']} ({q['symbol']}): ${q['price']:.2f} ({fmt_pct(q['change_pct'])}) 전일:${q['prev_close']:.2f} 거래량:{q['volume']:,}{w52}{day}{trend}{tech}{fund_str}"


def top_bottom(quotes, n=TOP_N):
    """Return top gainers, losers, and volume leaders."""
    by_chg = sorted(quotes, key=lambda x: x["change_pct"], reverse=True)
    by_vol = sorted(quotes, key=lambda x: x["volume"], reverse=True)
    return by_chg[:n], by_chg[-n:], by_vol[:n]


# ─── Fundamentals (yfinance) ─────────────────────────────────

def fetch_fundamentals_batch(symbols, max_workers=10):
    """Fetch fundamental data for a list of symbols via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        return {}

    def _fetch_one(sym):
        try:
            info = yf.Ticker(sym).info
            return sym, {k: info[k] for k in FUND_KEYS if info.get(k) is not None}
        except Exception:
            return sym, {}

    result = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for sym, data in pool.map(lambda s: _fetch_one(s), symbols):
            if data:
                result[sym] = data
    return result


def fmt_fund(fund, currency=""):
    """Format fundamental data into a compact string."""
    parts = []
    if "marketCap" in fund:
        mc = fund["marketCap"]
        if currency == "KRW":
            if mc >= 1e12:
                parts.append(f"시총:{mc/1e12:.1f}조")
            elif mc >= 1e8:
                parts.append(f"시총:{mc/1e8:.0f}억")
            else:
                parts.append(f"시총:{mc/1e6:.0f}백만")
        else:
            if mc >= 1e12:
                parts.append(f"시총:${mc/1e12:.2f}T")
            elif mc >= 1e9:
                parts.append(f"시총:${mc/1e9:.0f}B")
            else:
                parts.append(f"시총:${mc/1e6:.0f}M")
    if "trailingPE" in fund:
        parts.append(f"PER:{fund['trailingPE']:.1f}")
    elif "forwardPE" in fund:
        parts.append(f"fPER:{fund['forwardPE']:.1f}")
    if "priceToBook" in fund:
        parts.append(f"PBR:{fund['priceToBook']:.2f}")
    if "returnOnEquity" in fund:
        parts.append(f"ROE:{fund['returnOnEquity']*100:.1f}%")
    if "debtToEquity" in fund:
        parts.append(f"부채비율:{fund['debtToEquity']:.0f}%")
    if "revenueGrowth" in fund:
        parts.append(f"매출성장:{fund['revenueGrowth']*100:+.1f}%")
    if "earningsGrowth" in fund:
        parts.append(f"이익성장:{fund['earningsGrowth']*100:+.1f}%")
    if "profitMargins" in fund:
        parts.append(f"이익률:{fund['profitMargins']*100:.1f}%")
    if "dividendYield" in fund:
        dy = fund["dividendYield"]
        dy_pct = dy * 100 if dy < 1 else dy  # normalize: fraction → %
        parts.append(f"배당:{dy_pct:.2f}%")
    if "beta" in fund:
        parts.append(f"β:{fund['beta']:.2f}")
    return " | ".join(parts)


# ─── Main Collection ─────────────────────────────────────────

def _output_top_bottom(lines, quotes, name_map, currency, fund_map, n):
    """Output top gainers, losers, volume leaders (filtered mode)."""
    top_g, top_l, top_v = top_bottom(quotes, n)
    lines.append(f"### 상승 상위 {n}")
    for q in top_g:
        lines.append(format_stock_line(q, name_map, currency, fund_map))
    lines.append(f"### 하락 상위 {n}")
    for q in reversed(top_l):
        lines.append(format_stock_line(q, name_map, currency, fund_map))
    lines.append(f"### 거래량 상위 {n}")
    for q in top_v:
        lines.append(format_stock_line(q, name_map, currency, fund_map))


def _output_all(lines, quotes, name_map, currency, fund_map):
    """Output all stocks sorted by change_pct descending (full mode)."""
    sorted_q = sorted(quotes, key=lambda x: x["change_pct"], reverse=True)
    for q in sorted_q:
        lines.append(format_stock_line(q, name_map, currency, fund_map))


def collect_all(top_n=TOP_N) -> str:
    """Collect market data. top_n=0 for all stocks (stock-picks), default 15 (briefing)."""
    full_mode = (top_n == 0)
    lines = []
    now = datetime.now(KST)
    lines.append(f"# 시장 데이터 — {now.strftime('%Y-%m-%d %H:%M KST')}")
    lines.append("")

    # ── Load ticker lists ──
    kospi_tickers, kospi_names = load_ticker_list("kospi200.json")
    kosdaq_tickers, kosdaq_names = load_ticker_list("kosdaq150.json")
    sp500_tickers, _ = load_ticker_list("sp500_tickers.json")

    # ── Fetch all quotes in parallel ──
    # Combine all symbols into a single parallel fetch instead of 6 sequential ones
    all_quote_symbols = (
        list(MACRO_SYMBOLS.values())
        + list(INDICES.values())
        + list(SECTOR_ETFS.values())
        + kospi_tickers
        + kosdaq_tickers
        + sp500_tickers
    )
    all_quotes_list = fetch_quotes_parallel(all_quote_symbols, max_workers=40)
    all_quotes_map = {q["symbol"]: q for q in all_quotes_list}

    # Split results back
    macro_quotes = [all_quotes_map[s] for s in MACRO_SYMBOLS.values() if s in all_quotes_map]
    idx_quotes = [all_quotes_map[s] for s in INDICES.values() if s in all_quotes_map]
    sec_quotes = [all_quotes_map[s] for s in SECTOR_ETFS.values() if s in all_quotes_map]
    kr_set = set(kospi_tickers)
    kq_set = set(kosdaq_tickers)
    sp_set = set(sp500_tickers)
    kr_quotes = [q for q in all_quotes_list if q["symbol"] in kr_set]
    kq_quotes = [q for q in all_quotes_list if q["symbol"] in kq_set]
    us_quotes = [q for q in all_quotes_list if q["symbol"] in sp_set]

    # ── Fetch fundamentals (parallel with news/reddit via executor) ──
    fund_executor = ThreadPoolExecutor(max_workers=1)
    if full_mode:
        fund_symbols = [q["symbol"] for q in kr_quotes + kq_quotes + us_quotes]
    else:
        all_top_symbols = set()
        for group in top_bottom(kr_quotes) + top_bottom(kq_quotes) + top_bottom(us_quotes):
            for q in group:
                all_top_symbols.add(q["symbol"])
        fund_symbols = list(all_top_symbols)
    fund_future = fund_executor.submit(fetch_fundamentals_batch, fund_symbols, 20)

    # ── Fetch news + reddit in parallel ──
    news_results = {}
    reddit_results = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        news_futures = {}
        for cat, urls in NEWS_FEEDS.items():
            for url in urls:
                news_futures[pool.submit(fetch_rss, url)] = (cat, url)
        reddit_futures = {pool.submit(fetch_reddit, sub, limit): sub for sub, limit in REDDIT_SUBS}

        for f in as_completed(list(news_futures) + list(reddit_futures)):
            if f in news_futures:
                cat, url = news_futures[f]
                news_results.setdefault(cat, []).extend(f.result())
            else:
                sub = reddit_futures[f]
                reddit_results[sub] = f.result()

    # Wait for fundamentals
    fund_map = fund_future.result()
    fund_executor.shutdown(wait=False)

    # ── Output: Macro ──
    lines.append("## 매크로 지표 (원자재/환율/채권/암호화폐)")
    macro_by_sym = {q["symbol"]: q for q in macro_quotes}
    for name, sym in MACRO_SYMBOLS.items():
        q = macro_by_sym.get(sym)
        if q:
            w52 = ""
            if q.get("week52_high") and q.get("week52_low"):
                w52 = f"  52주:{q['week52_low']}~{q['week52_high']}"
            lines.append(f"- {name}: {q['price']} ({fmt_pct(q['change_pct'])}) 전일:{q['prev_close']}{w52}")
    lines.append("")

    # ── Output: Indices ──
    lines.append("## 주요 지수")
    idx_by_sym = {q["symbol"]: q for q in idx_quotes}
    for name, sym in INDICES.items():
        q = idx_by_sym.get(sym)
        if q:
            trend = " → ".join(str(c) for c in q["closes_5d"])
            day = ""
            if q.get("day_high") and q.get("day_low"):
                day = f"  당일:{q['day_low']:,.2f}~{q['day_high']:,.2f}"
            lines.append(f"- {name}: {q['price']:,.2f} ({fmt_pct(q['change_pct'])}) 전일:{q['prev_close']:,.2f}{day}  [5일: {trend}]")
    lines.append("")

    # ── Output: Sector ETFs ──
    lines.append("## 섹터 ETF 등락")
    sec_by_sym = {q["symbol"]: q for q in sec_quotes}
    sectors = [(n, sec_by_sym[s]) for n, s in SECTOR_ETFS.items() if s in sec_by_sym]
    sectors.sort(key=lambda x: x[1]["change_pct"], reverse=True)
    for name, q in sectors:
        lines.append(f"- {name} ({q['symbol']}): {fmt_pct(q['change_pct'])} 가격:{q['price']}")
    lines.append("")

    # ── Output KOSPI 200 ──
    lines.append(f"## KOSPI 200 ({len(kr_quotes)}종목 수집)")
    if full_mode:
        _output_all(lines, kr_quotes, kospi_names, "KRW", fund_map)
    else:
        _output_top_bottom(lines, kr_quotes, kospi_names, "KRW", fund_map, top_n)
    lines.append("")

    # ── Output KOSDAQ 150 ──
    lines.append(f"## KOSDAQ 150 ({len(kq_quotes)}종목 수집)")
    if full_mode:
        _output_all(lines, kq_quotes, kosdaq_names, "KRW", fund_map)
    else:
        _output_top_bottom(lines, kq_quotes, kosdaq_names, "KRW", fund_map, top_n)
    lines.append("")

    # ── Output S&P 500 ──
    lines.append(f"## S&P 500 ({len(us_quotes)}종목 수집)")
    if full_mode:
        _output_all(lines, us_quotes, {}, "USD", fund_map)
    else:
        _output_top_bottom(lines, us_quotes, {}, "USD", fund_map, top_n)
    lines.append("")

    # ── Summary stats ──
    lines.append("## 시장 요약 통계")
    for label, quotes in [("KOSPI 200", kr_quotes), ("KOSDAQ 150", kq_quotes), ("S&P 500", us_quotes)]:
        if not quotes:
            continue
        up = sum(1 for q in quotes if q["change_pct"] > 0)
        down = sum(1 for q in quotes if q["change_pct"] < 0)
        flat = len(quotes) - up - down
        avg_chg = sum(q["change_pct"] for q in quotes) / len(quotes)
        lines.append(f"- {label}: 상승 {up} / 하락 {down} / 보합 {flat} | 평균 등락률: {avg_chg:+.2f}%")
    lines.append("")

    # ── News (already fetched in parallel above) ──
    for cat in NEWS_FEEDS:
        lines.append(f"## 뉴스: {cat}")
        seen = set()
        for a in news_results.get(cat, []):
            key = a["title"][:60]
            if key not in seen:
                seen.add(key)
                src = f" ({a['source']})" if a.get("source") else ""
                date = f" [{a['date']}]" if a.get("date") else ""
                lines.append(f"- {a['title']}{src}{date}")
        lines.append("")

    # ── Reddit (already fetched in parallel above) ──
    lines.append("## Reddit 감성")
    for sub, limit in REDDIT_SUBS:
        lines.append(f"### r/{sub}")
        for p in reddit_results.get(sub, []):
            flair = f" [{p['flair']}]" if p.get("flair") else ""
            lines.append(f"- {p['title']}{flair} (▲{p['score']} 💬{p['comments']} ratio:{p['upvote_ratio']})")
        lines.append("")

    return "\n".join(lines)



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Collect market data")
    parser.add_argument("--top", type=int, default=15, help="Top N stocks per section (0=all)")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to query (e.g. 005930.KS NVDA)")
    parser.add_argument("--name", nargs="+", help="Search by Korean name (e.g. 삼성전자 SK하이닉스)")
    args = parser.parse_args()

    if args.symbols or args.name:
        # Build name maps for reverse lookup
        kospi_tickers, kospi_names = load_ticker_list("kospi200.json")
        kosdaq_tickers, kosdaq_names = load_ticker_list("kosdaq150.json")
        all_names = {**kospi_names, **kosdaq_names}
        # Reverse map: name → symbol
        name_to_sym = {v: k for k, v in all_names.items()}

        symbols = list(args.symbols or [])
        if args.name:
            for name in args.name:
                if name in name_to_sym:
                    symbols.append(name_to_sym[name])
                else:
                    # Partial match
                    matches = [(k, v) for v, k in name_to_sym.items() if name in v]
                    if matches:
                        for sym, _ in matches:
                            symbols.append(sym)
                    else:
                        print(f"[WARN] '{name}' not found in ticker lists, trying as symbol", file=sys.stderr)
                        symbols.append(name)

        if not symbols:
            print("No symbols to query", file=sys.stderr)
            sys.exit(1)

        quotes = fetch_quotes_parallel(symbols)
        fund_map = fetch_fundamentals_batch(symbols)
        lines = []
        for q in quotes:
            currency = "KRW" if q["symbol"].endswith((".KS", ".KQ")) else ""
            lines.append(format_stock_line(q, all_names, currency, fund_map))
        print("\n".join(lines))
    else:
        print(collect_all(top_n=args.top))
