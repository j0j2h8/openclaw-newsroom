# OpenClaw Newsroom

24시간 자율 운영되는 AI 편집국 시스템.
OpenClaw 플랫폼 위에서 35개 에이전트가 Slack을 통해 협업하며, 금융 편집국(시장 분석 · 종목 추천 · 속보 · 리스크 · 투자 대가 토론)과 트렌드 편집국(트렌드 포착 · SEO 블로그 · 수익 최적화)을 자동 운영한다.

## 조직도

```
                    🏛️ 편집국장 (newsroom-chief)
                         #ai-desk
          ┌──────────┬──────────┬──────────┐
          │          │          │          │
    📈 리서치부  🚨 속보부   📰 편집부  🛡️ 리스크부
    #ai-research #ai-breaking #ai-editorial #ai-risk
          │          │          │          │
   chief-analyst  news-desk  editor-    risk-
          │                  in-chief   manager
          │
    ┌─────┼─────┬────────┐
    │     │     │        │
  tech  funda  news   researcher
 analyst mental analyst
         analyst
                    ┌────────────┐
                    │  지원 부서   │
                    ├────────────┤
                    │ 📊 성과분석실 │ performance-tracker
                    │ 🌐 매크로전략실│ macro-strategist
                    └────────────┘

    🎙️ 토론부 (#ai-debate)
    debate-moderator (의장)
    ┌───┬───┬───┬───┬───┬───┬───┐
    │🦉 │🚀 │🌊 │🦅 │🌍 │🎲 │🛒 │
    │버핏│우드│달리│드러│템플│리버│린치│
    │   │   │오 │켄밀│턴 │모어│   │
    │   │   │   │러 │   │   │   │
    └───┴───┴───┴───┴───┴───┴───┘
    * 주제별 3~4명 선별 호출

    편집 파이프라인: trend-researcher → content-writer → humanizer → editor-in-chief
    여행 파이프라인: destination-researcher → itinerary-builder → travel-planner

    📡 트렌드 편집국 (#ai-blog)
    trend-chief (편집장)
    ┌──────┬──────┬──────┬──────┬──────┬──────┐
    │🔍    │🔑    │✏️    │🏷️    │✅    │💰    │
    │trend │key-  │blog  │seo   │fact  │reve- │
    │scout │word  │writer│opti- │check │nue   │
    │      │analy.│      │mizer │er    │ops   │
    └──────┴──────┴──────┴──────┴──────┴──────┘
    🔄 update-tracker (갱신 관리)
```

## Slack 채널

| 채널 | 용도 |
|------|------|
| `#ai-desk` | 편집국장 지휘소. 모닝/이브닝 브리핑, 매크로 시그널, 시스템 헬스체크 |
| `#ai-research` | 종목 추천, 시장 브리핑, 워치리스트, 성과 추적 |
| `#ai-breaking` | 속보 감지, 긴급 알림, 세션 전환 브리핑 |
| `#ai-editorial` | 뉴스레터, 심층 분석, 섹터 리포트 |
| `#ai-risk` | 시장 위기 스캔, 리스크 경보, 위클리 리스크 리뷰 |
| `#ai-debate` | 투자 대가 토론 (종목 검증, 시장 전망) |
| `#ai-blog` | 트렌드 편집국 (편집회의, 블로그 초안, 수익 리포트) |
| `#ai-trip` | 여행 일정 추천 |

## 크론 스케줄 (KST)

### 매일
| 시간 | 작업 | 에이전트 | 채널 |
|------|------|---------|------|
| 매 30분 | 속보 스캔 | news-desk | #ai-breaking |
| 매 정시 | 시장 위기 스캔 | risk-manager | #ai-risk |
| 매 30분 | 시스템 헬스체크 | newsroom-chief | #ai-desk |
| 04:00 | 오늘의 뉴스레터 | editor-in-chief | #ai-editorial |
| 06:00 | 트렌드 편집회의 | trend-chief | #ai-blog |
| 06:00 | 미국장 마감 브리핑 | chief-analyst | #ai-research |
| 06:00 | 세션 전환 (프리마켓) | news-desk | #ai-breaking |
| 06:30 | 미국 추천 종목 | chief-analyst | #ai-research |
| 06:30 | 미국 성과 업데이트 | performance-tracker | #ai-research |
| 07:00 | 프리마켓 종목 토론 | debate-moderator | #ai-debate |
| 07:00 | 모닝 편집회의 | newsroom-chief | #ai-desk |
| 07:30 | 매크로 이벤트 프리뷰 | macro-strategist | #ai-desk |
| 08:30 | 장 시작 전 브리핑 | chief-analyst | #ai-research |
| 09:00 | 세션 전환 (아시아장) | news-desk | #ai-breaking |
| 09:00~15:00 | 워치리스트 점검 (장중) | chief-analyst | #ai-research |
| 14:00 | 오후 트렌드 체크 | trend-chief | #ai-blog |
| 15:30 | 세션 전환 (유럽장) | news-desk | #ai-breaking |
| 16:00 | 장 마감 브리핑 | chief-analyst | #ai-research |
| 16:30 | 마켓 데일리 요약 | editor-in-chief | #ai-editorial |
| 16:30 | 일일 성과 업데이트 | performance-tracker | #ai-research |
| 17:00 | 내일의 추천 종목 | chief-analyst | #ai-research |
| 17:30 | 추천 종목 등록 | performance-tracker | #ai-research |
| 17:30 | 추천 종목 토론 | debate-moderator | #ai-debate |
| 18:00 | 트렌드 일일 리포트 | trend-chief | #ai-blog |
| 19:00 | 이브닝 마감회의 | newsroom-chief | #ai-desk |
| 22:00~05:00 | 워치리스트 점검 (미국장) | chief-analyst | #ai-research |
| 22:30 | 세션 전환 (미국장) | news-desk | #ai-breaking |

### 주간
| 시간 | 작업 | 에이전트 | 채널 |
|------|------|---------|------|
| 월 09:00 | 주간 갱신 점검 | trend-chief | #ai-blog |
| 월/목 08:00 | 매크로 레짐 판단 | macro-strategist | #ai-desk |
| 수 17:30 | 심층 종목 분석 | chief-analyst | #ai-research |
| 수 18:30 | 딥다이브 리포트 | editor-in-chief | #ai-editorial |
| 금 17:00 | 투자 환경 시그널 | macro-strategist | #ai-desk |
| 금 17:30 | 섹터 로테이션 리포트 | chief-analyst | #ai-research |
| 금 18:30 | 섹터 위클리 | editor-in-chief | #ai-editorial |
| 금 18:00 | 주간 시장 전망 토론 | debate-moderator | #ai-debate |
| 금 19:00 | 위클리 리스크 리뷰 | risk-manager | #ai-risk |
| 토 09:00 | 주간 성적표 | performance-tracker | #ai-research |
| 토 10:00 | 위클리 리뷰 | editor-in-chief | #ai-editorial |
| 토 11:00 | 위클리 성과 리뷰 | newsroom-chief | #ai-desk |

### 월간
| 시간 | 작업 | 에이전트 | 채널 |
|------|------|---------|------|
| 매월 1일 10:00 | 월간 전략 피드백 | performance-tracker | #ai-research |
| 매월 1일 10:00 | 월간 수익 리뷰 | trend-chief | #ai-blog |

## 디렉토리 구조

```
.openclaw/
├── CLAUDE.md                          # 프로젝트 지침
├── openclaw.json                      # 메인 설정 (gitignore — 토큰 포함)
├── openclaw.template.json             # 토큰 마스킹된 설정 템플릿
├── agents/
│   ├── <agent-id>/
│   │   └── workspace/
│   │       ├── AGENTS.md              # 에이전트 운영 지침 (핵심)
│   │       ├── SOUL.md                # 성격/행동 가이드라인
│   │       ├── IDENTITY.md            # 이름, 이모지
│   │       ├── USER.md                # 사용자 정보
│   │       └── *.json                 # 에이전트별 데이터
│   └── ...
├── workspace/
│   ├── scripts/
│   │   ├── market_data.py             # 실시간 시장 데이터 수집 (yfinance)
│   │   ├── healthcheck.sh             # 시스템 헬스체크
│   │   ├── stock-picks.py             # 종목 추천 파이프라인
│   │   └── morning-briefing.py        # 모닝 브리핑 스크립트
│   └── data/                          # 종목 추천/분석 데이터
├── cron/
│   ├── jobs.json                      # 크론 작업 설정
│   └── runs/                          # 실행 기록
└── docs/plans/                        # 설계 문서
```

## 핵심 설계 원칙

1. **데이터 수집 후 분석** — 모든 시장 수치는 `market_data.py`로 실제 데이터를 수집한 후 사용. 추측/할루시네이션 방지
2. **부서 분리** — 각 에이전트는 자기 책임 범위만 수행. 편집국장이 조율
3. **HEARTBEAT_OK 패턴** — 이벤트 없으면 조용히 넘어감. 불필요한 Slack 노이즈 방지
4. **격리된 세션** — 크론 작업은 `--session-id "$(uuidgen)"`로 매번 새 세션. 컨텍스트 오염 방지
5. **3단계 속보 대응** — 속보부 감지 → 편집국장 조율 → 리서치부/리스크부/편집부 병렬 처리

## 설정 복원

새 환경에서 복원할 때:

```bash
# 1. repo clone
git clone https://github.com/j0j2h8/openclaw-newsroom.git ~/.openclaw

# 2. 템플릿에서 설정 파일 생성
cp ~/.openclaw/openclaw.template.json ~/.openclaw/openclaw.json

# 3. openclaw.json에 실제 토큰 입력
#    - channels.slack.botToken
#    - channels.slack.appToken
#    - gateway.auth.token

# 4. 게이트웨이 시작
openclaw gateway start
```

## 기술 스택

- **플랫폼:** [OpenClaw](https://openclaw.ai) 2026.3.7
- **AI 모델:** OpenAI Codex / GPT-5.4
- **메시징:** Slack (Socket Mode)
- **시장 데이터:** yfinance (Python)
- **런타임:** macOS LaunchAgent (자동 재시작)
