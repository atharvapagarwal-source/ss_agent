# SocialCoach AI — Autonomous Multi-Tenant Social Media & Lead-Gen Agent SaaS

> **Autonomous multi-tenant SaaS application and AI agent platform designed specifically for Career Coaches.**  
> Built with **Next.js (App Router)**, **FastAPI**, **LangGraph**, **Playwright**, **Celery + Redis**, and **PostgreSQL**.

---

## ⚡ System Architecture Overview

```
                                  ┌───────────────────────────────┐
                                  │      Client Web Portal        │
                                  │  (Next.js 14, Tailwind, UI)   │
                                  └───────────────┬───────────────┘
                                                  │ HTTP / REST / SSE
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │       FastAPI Gateway         │
                                  │   (Auth, HITL, Webhooks, CRM) │
                                  └───────┬───────────────┬───────┘
                                          │               │
                     ┌────────────────────┘               └───────────────────┐
                     ▼                                                        ▼
    ┌─────────────────────────────────┐                      ┌─────────────────────────────────┐
    │     LangGraph 4-Agent Core      │                      │    Celery Workers + Beat        │
    │  • Agent 1: Trend Hunter        │                      │  • 15-min Newsjack Poller       │
    │  • Agent 2: Content Creator     │                      │  • Jittered DM Dispatcher       │
    │  • Agent 3: HITL & Compliance   │                      │  • High-frequency Telemetry     │
    │  • Agent 4: Comment-to-DM Setup │                      │  • Scheduled Post Publisher     │
    └────────────────┬────────────────┘                      └────────────────┬────────────────┘
                     │                                                        │
                     ▼                                                        ▼
    ┌─────────────────────────────────┐                      ┌─────────────────────────────────┐
    │   Playwright Carousel Service   │                      │    PostgreSQL + Redis Broker    │
    │  • 1080×1350 Instagram PNGs     │                      │  • Multi-Tenant RLS Schemas     │
    │  • Multi-Page LinkedIn PDFs     │                      │  • AES-256 Vault / Token Log    │
    └─────────────────────────────────┘                      └─────────────────────────────────┘
```

---

## 🚀 Key Features

1. **4-Agent LangGraph Pipeline**:
   - **Agent 1 (Trend Hunter)**: Real-time job market newsjacking (layoffs, hiring surges, RTO mandates, salary benchmarks).
   - **Agent 2 (Content Creator)**: Formats tailored posts for LinkedIn (text + doc carousel), Instagram (caption + 1080×1350 PNG slides), X/Twitter (5-tweet thread), and Facebook.
   - **Agent 3 (HITL & Critic)**: Analyzes hook strength, career coaching tone, compliance guardrails, and quality score (0–10).
   - **Agent 4 (Comment-to-DM Lead Magnet Automation)**: Binds fuzzy-matched keyword triggers (70%+ similarity) to automated direct message dispatch.

2. **Carousel Rendering Engine (Playwright Microservice)**:
   - High-fidelity 1080×1350px canvas rendering with dynamic tenant brand colors, Google Fonts, glassmorphism cards, and niche tags.
   - Stitches multi-page high-resolution PDFs using `pdf-lib` for LinkedIn document carousels.
   - Exports compressed PNG decks for Instagram carousels.

3. **Comment-to-DM Lead CRM & Automation**:
   - Webhook ingest for Meta, LinkedIn, and Twitter with HMAC-SHA256 signature verification.
   - Jittered rate limiter (randomized 30s–5m delays) to prevent platform bans.
   - Inbound lead capture table with status indicators (`QUEUED`, `SENT`, `DELIVERED`, `CONVERTED`) and 1-click CSV export.

4. **Telemetry & Second-Level Analytics Dashboard**:
   - Time-series Reach Velocity curves (24-hour window).
   - Step-by-step conversion funnel: Post Views ➔ Comments ➔ Keyword Triggers ➔ DMs Sent ➔ Resource Download.
   - Cross-platform reach comparison (LinkedIn, Instagram, X, Facebook).

---

## 🛠️ Repository Structure

```
.
├── apps/
│   ├── api/                   # Python FastAPI backend & LangGraph agents
│   │   ├── agents/            # LangGraph multi-agent workflow
│   │   ├── routers/           # HITL, Webhooks, Leads, Posts, Analytics, Auth
│   │   ├── services/          # OAuth Vault, Meta, LinkedIn, Twitter API
│   │   ├── workers/           # Celery application, beat scheduler, tasks
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── web/                   # Next.js 14 frontend application
│       ├── src/
│       │   ├── app/           # App router, layout, globals.css
│       │   ├── components/    # Analytics, HITL Queue, Studio, CRM, Settings
│       │   └── lib/           # API mock/live client & utility helpers
│       ├── tailwind.config.js
│       └── package.json
│
├── services/
│   └── carousel-renderer/     # Playwright Chromium rendering microservice
│       ├── src/               # Express API, Playwright engine, slide templates
│       ├── Dockerfile
│       └── package.json
│
├── infra/
│   ├── docker-compose.yml     # Complete local stack orchestration
│   └── scripts/seed.sql       # PostgreSQL multi-tenant schema & initial seed
│
└── .env.example               # Full environment variable configuration template
```

---

## 🏁 Quickstart (Local Development)

### Prerequisites
- Docker & Docker Compose
- Node.js v18+ & Python 3.11+ (if running bare-metal)

### 1. Configure Environment
```bash
cp .env.example .env
```

### 2. Start with Docker Compose
```bash
docker compose -f infra/docker-compose.yml up --build
```

Services will be accessible at:
- **Next.js Frontend**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend**: [http://localhost:8000](http://localhost:8000) (Swagger Docs at `/docs`)
- **Carousel Renderer Microservice**: [http://localhost:3001](http://localhost:3001)
- **Flower (Celery Monitoring)**: [http://localhost:5555](http://localhost:5555)
- **PostgreSQL**: `localhost:5432` (db: `socialcoach`, user: `socialcoach`)
- **Redis**: `localhost:6379`
