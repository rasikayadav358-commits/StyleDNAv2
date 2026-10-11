# 00-overview — Product, repo, defaults, and release checklist

## 0. Product in one paragraph

StyleDNA takes a user's style preferences and body proportions, digitizes their wardrobe from photos and video, generates outfits from what they already own, explains each recommendation, finds wardrobe gaps, and suggests matching products from a local catalog or live search. The recommender learns from user feedback and improves over time.

Source PRD: StyleSenseAI_Product_Requirements.docx (FR-01 through FR-17, MVP scope §26).

## 1. Fixed decisions

| Area | Decision |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2 |
| DB | PostgreSQL + pgvector in production; SQLite + aiosqlite for tests |
| Jobs | Arq with Redis; a local eager mode is allowed in tests/dev |
| Object storage | S3-compatible object storage; MinIO locally; local filesystem fallback |
| Frontend | Next.js App Router + TypeScript + Tailwind |
| Auth | Email/password, argon2id, short JWT access token, rotating refresh cookie |
| ML libs | open_clip, MediaPipe, rembg, scikit-learn, LightGBM, Pillow, ffmpeg |
| LLM | Thin LLMClient wrapper with a mock implementation always available |
| Infra | docker compose up brings up API, worker, postgres, redis, minio, and optional scanning |
| Currency/locale | INR default; India-first categories are first-class |

Provider interfaces are mandatory for LLM calls, storage, catalog search, and background jobs. The platform must run in demo mode without external keys or internet access.

## 2. Repository layout

```text
StyleDNA/
  CLAUDE.md
  PLAN.md
  README.md
  docker-compose.yml
  .env.example
  Makefile
  docs/
    DECISIONS.md
    PROGRESS.md
    phases/
      00-overview.md
      00.md
      01.md
      02.md
      03.md
      04.md
      05.md
      06.md
      07.md
      08.md
      09.md
      10.md
  apps/
    api/
      app/
        main.py
        config.py
        deps.py
        core/
        db/
        routers/
        services/
        workers/
      tests/
      data/
      scripts/
```

## 11. Security requirements summary

- argon2id passwords; no user enumeration; login and refresh-rate limits
- Short-lived JWT; refresh rotation with reuse detection; httpOnly/Secure/SameSite cookies
- Ownership checks on every user-scoped query
- Upload validation: magic bytes, size caps, duration caps, decompression-bomb protection, EXIF stripping
- Private object storage with random keys and encrypted body media by default
- Face blur and privacy-safe body-media purge workflows
- Consent gates for body media, third-party AI, and analytics
- All external model output is treated as untrusted and is schema-validated
- Secrets come only from environment configuration; dependency and secret audits run in CI
- Security headers, CORS restrictions, trusted-host checks, and audit logging are required

## 12. ML requirements summary

| Component | Method | Learns from |
|---|---|---|
| Wardrobe embeddings | Fashion-CLIP or equivalent | pretrained + corrections |
| Attribute tagging | Zero-shot classification → learned head → optional LLM fallback | labels and corrections |
| Body proportions | MediaPipe pose + segmentation → soft-rule shape classifier | user corrections |
| Outfit ranking | Rule score + learned ranker | likes, saves, wears, dislikes, skips |
| Personalization | Style DNA via event-driven EMA | every interaction |
| Exploration | epsilon-greedy or Thompson-sampling slot | logged propensity |
| Product retrieval | pgvector ANN + learned rerank | clicks, saves, wishlist |
| Gap analysis | Counterfactual outfit counts via the generator | — |
| Safety of learning | Champion/challenger, holdout metrics, rollback | — |

## 13. Definition of done

1. A clean clone can run the demo flow with no API keys.
2. The app can generate useful outfits and recommendations without live external services.
3. Security, media, and wardrobe acceptance criteria are green in CI.
4. Learning and ranking improve over a simulated user loop.
5. README, ML card, privacy doc, and threat model are complete.

## 14. Out of scope

Virtual try-on, social sharing, resale, weather planning, and general chatbot features remain out of scope unless explicitly added later.
