# BrandSentinel AI

**CodeNexus India 2026 â€” Round 2: The Build**

[![Hackathon](https://img.shields.io/badge/Hackathon-CodeNexus%202026-blue)](https://codenexus.com)
[![Stack](https://img.shields.io/badge/Stack-FastAPI%20%2B%20React%20%2B%20Gemini-green)](.)

---

## ðŸŽ¯ Overview

**BrandSentinel AI** is an explainable, human-controlled brand governance platform that reviews organizational content against approved brand guidelines, product facts, terminology, messaging requirements, tone and voice standards.

### Key Features

âœ… **Evidence-Linked Findings** â€” Every issue cites actual guideline sources
âœ… **Hybrid Audit Engine** â€” Deterministic rules + Gemini AI analysis
âœ… **Human-in-the-Loop Approval** â€” AI never makes final publication decisions
âœ… **Zero-Auth Judge Mode** â€” Functional in incognito without accounts
âœ… **Persistent Audit Trail** â€” SQLite-backed decision history

---

## ðŸ— Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                    BrandSentinel AI                          â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                              â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”‚
â”‚  â”‚   React UI   â”‚â”€â”€â”€â”€â”€â–¶â”‚  FastAPI Backend            â”‚     â”‚
â”‚  â”‚  TypeScript  â”‚      â”‚  - REST API Endpoints        â”‚     â”‚
â”‚  â”‚  Tailwind CSSâ”‚â—€â”€â”€â”€â”€â”€â”‚  - SQLite Persistence        â”‚     â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â”‚  - Pydantic V2 Validation    â”‚     â”‚
â”‚                        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â”‚
â”‚                                   â”‚                         â”‚
â”‚                        â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”‚
â”‚                        â”‚   Audit Orchestrator         â”‚     â”‚
â”‚                        â”‚  - Deterministic Rules       â”‚     â”‚
â”‚                        â”‚  - Vector/Keyword Retrieval  â”‚     â”‚
â”‚                        â”‚  - Gemini 2.0 Flash          â”‚     â”‚
â”‚                        â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â”‚
â”‚                                                              â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## ðŸš€ Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Google Gemini API Key** ([Get one here](https://ai.google.dev))

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
python -m uvicorn app.main:app --reload
```

Backend runs at: `http://localhost:8000`
API Docs: `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## ðŸ“¦ Technology Stack

### Backend
- **FastAPI** â€” Modern Python web framework
- **Pydantic V2** â€” Data validation with type safety
- **SQLAlchemy** â€” ORM for SQLite persistence
- **Google Gemini API** â€” AI-powered contextual analysis
- **NumPy** â€” Lightweight semantic retrieval

### Frontend
- **React 18** â€” UI library
- **TypeScript** â€” Type-safe development
- **Vite** â€” Fast build tool
- **Tailwind CSS** â€” Utility-first styling
- **Lucide React** â€” Clean icon system
- **Axios** â€” HTTP client

---

## ðŸŽ® Usage Workflow

1. **Open Application** â€” No authentication required
2. **Load Brand Guidelines** â€” Pre-seeded ApexCloud guidelines available
3. **Submit Content** â€” Paste marketing copy or load sample drafts
4. **Run Audit** â€” Hybrid engine detects violations
5. **Review Findings** â€” Each issue shows severity, explanation, evidence
6. **Apply Corrections** â€” Accept or dismiss suggested replacements
7. **Human Approval** â€” Reviewer approves, rejects, or requests changes
8. **Audit History** â€” All decisions persisted and auditable

---

## ðŸ“ Project Structure

```
BrandSentinel AI/
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ main.py                    # FastAPI app + routes
â”‚   â”‚   â”œâ”€â”€ schemas.py                 # Pydantic domain models
â”‚   â”‚   â”œâ”€â”€ models.py                  # SQLAlchemy ORM
â”‚   â”‚   â”œâ”€â”€ database.py                # Database configuration
â”‚   â”‚   â”œâ”€â”€ config.py                  # Environment settings
â”‚   â”‚   â”œâ”€â”€ seed_data.py               # ApexCloud guidelines
â”‚   â”‚   â””â”€â”€ services/
â”‚   â”‚       â”œâ”€â”€ rules_engine.py        # Deterministic checks
â”‚   â”‚       â”œâ”€â”€ vector_store.py        # Keyword/semantic retrieval
â”‚   â”‚       â”œâ”€â”€ llm_auditor.py         # Gemini integration
â”‚   â”‚       â””â”€â”€ audit_orchestrator.py  # Merge + orchestration
â”‚   â”œâ”€â”€ tests/
â”‚   â”œâ”€â”€ requirements.txt
â”‚   â””â”€â”€ .env.example
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ src/
â”‚   â”‚   â”œâ”€â”€ components/
â”‚   â”‚   â”œâ”€â”€ types/
â”‚   â”‚   â”œâ”€â”€ api/
â”‚   â”‚   â””â”€â”€ App.tsx
â”‚   â”œâ”€â”€ package.json
â”‚   â””â”€â”€ .env.example
â”œâ”€â”€ workflow/
â”‚   â””â”€â”€ claude_code_master_build_plan.md
â””â”€â”€ README.md
```

---

## ðŸ”§ Environment Variables

### Backend (.env)
```env
GEMINI_API_KEY=your_gemini_api_key_here
PORT=8000
CORS_ORIGINS="*"
DATABASE_URL=sqlite:///./brandsentinel.sqlite
```

### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## ðŸ§ª Testing

```bash
cd backend
pytest tests/
```

---

## ðŸš¢ Deployment

### Backend
- **Platform**: Render / Railway / Fly.io
- **Container**: Docker-ready
- **Database**: SQLite (upgradeable to PostgreSQL)

### Frontend
- **Platform**: Vercel / Netlify
- **Build**: `npm run build`
- **Output**: `dist/`

---

## ðŸ“ License

MIT License â€” Built for CodeNexus India 2026

---

## ðŸ‘¥ Team

Built by a Principal Software Architect with Claude Code

---

## ðŸ™ Acknowledgments

- **Google Gemini** â€” AI-powered contextual analysis
- **FastAPI** â€” Lightning-fast Python web framework
- **React** â€” Modern UI development
- **CodeNexus India 2026** â€” Hackathon organizers

---

**Status**: ðŸš§ Active Development â€” Round 2 Build Phase
