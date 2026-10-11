# StyleSenseAI — status pointer

This file is intentionally stale.
Use docs/PROGRESS.md for the active project tracker.
Use docs/phases/00-overview.md for the current architecture and repo defaults.
Use the numbered phase files for the execution plan.

Source of truth: [docs/PROGRESS.md](docs/PROGRESS.md)
Plan overview: [docs/phases/00-overview.md](docs/phases/00-overview.md)
Current phase: [docs/phases](docs/phases)

---

## 3. Implementation Status Matrix

| Component / Layer | Status | Key Deliverables & Notes |
|---|:---:|---|
| **Phase 0: Bootstrap** | **100% Complete** | Docker Compose, Makefile, logging, PII redaction, configs, health endpoints. |
| **Phase 1: Auth & Security** | **100% Complete** | Argon2id, JWT+Refresh rotation, security middleware, IDOR defenses, models. |
| **Phase 2: Secure Media** | **100% Complete** | S3/MinIO & LocalFS storage, AES-256-GCM envelope encryption, EXIF scrub, face blur, video extraction, stream & delete. |
| **Phase 3: Wardrobe AI** | **100% Complete** | Cutouts, FashionCLIP+mock embeddings, 3-stage attribute cascade, corrections logging, inventory tracking. |
| **Phase 4: Body Analysis** | **100% Complete** | Manual measurement engine, visual silhouette estimation, soft ratio rules, measurement encryption, privacy purge. |
| **Phase 5: Outfit Engine v1** | **Pending** | Skeletons, color harmony, body fit rules, MMR diversification, explanations. |
| **Phase 6: Catalog & Gaps** | **Pending** | Local catalog with pgvector ANN, deep links, counterfactual gap analysis. |
| **Phase 7: Learning System** | **Pending** | Event logs, Style DNA EMA, Logistic/LightGBM ranker, synthetic bootstrap. |
| **Phase 8: Frontend** | **Pending** | Next.js App Router, Tailwind, accessible components, full user journey. |
| **Phase 9: Seed & Demo** | **Pending** | `seed_demo.py` script for instant showcase with demo user & wardrobe. |
| **Phase 10: Hardening** | **Pending** | Bandit/gitleaks audits, docs (Threat Model, ML Card, Privacy), CI workflows. |


---

## 4. Next Phases: Detailed Roadmap & Deliverables

To complete the project according to [PLAN.md](file:///Users/inshrakhan/sih/stylesense/PLAN.md), the remaining phases must be executed in sequential vertical slices:

### Phase 2 — Secure Media Pipeline [P0]
1. **Storage Drivers (`app/services/storage/`):**
   - Implement `S3Storage` (MinIO/AWS S3) and `LocalFSStorage` implementing `StorageProvider`.
   - Structured object key naming: `u/{user_id}/{kind}/{uuid4}`.
2. **Media Ingestion & Validation (`app/services/media/validate.py`):**
   - Validate magic bytes (reject polyglots and disguised executables).
   - Enforce dimensions (≤ 6000px), size (≤ 10MB image, ≤ 100MB body video, ≤ 200MB wardrobe video).
   - Protect against decompression bombs via Pillow `MAX_IMAGE_PIXELS`.
3. **Sanitization & Privacy Processing (`app/services/media/sanitize.py`):**
   - Strip all EXIF / GPS metadata, correct orientation, generate standard web thumbnails.
   - For body media: Apply automatic face detection and face blurring.
   - Encrypt body media bytes with user-specific keys (`app/core/crypto.py`).
4. **Video Processing (`app/services/media/video.py`):**
   - ffmpeg frame extraction (~1 fps, max 30 frames).
   - Pose confidence scoring to select optimal frontal frames and take median ratios.
5. **API & Endpoints (`app/routers/media.py`):**
   - `POST /api/v1/media`: Streaming file upload returning `media_id` in `pending` status.
   - `GET /api/v1/media/{id}`: Poll status or obtain presigned download URLs (TTL ≤ 5 min).
   - `DELETE /api/v1/media/{id}`: Purge media and database record.
   - `DELETE /api/v1/me`: Complete purge of all user assets and encrypted data.

---

### Phase 3 — Wardrobe AI (Clothes Digitization) [P0]
1. **Garment Cutout:** Background removal via `rembg` on uploaded clothing photos, saving clean cutouts as derived assets.
2. **Vector Embeddings:** Compute fashion embeddings using FashionCLIP (`open_clip`) in [app/services/vision/embeddings.py](file:///Users/inshrakhan/sih/stylesense/apps/api/app/services/vision/embeddings.py) and store in `wardrobe_items.embedding`.
3. **Three-Stage Attribute Cascade:**
   - *Stage A (Local):* Zero-shot CLIP classification against `data/category_taxonomy.yaml` (category, pattern, neckline, sleeve, fit, occasion) + k-means dominant Lab color extraction.
   - *Stage B (Local Learned Head):* Logistic regression model on embeddings from accumulated user corrections.
   - *Stage C (Claude Vision):* Escalate low-confidence attributes to Claude Vision (only when `third_party_ai` consent is granted and `CLASSIFIER_PROVIDER != local`), validated against strict JSON schemas.
4. **Endpoints (`app/routers/wardrobe.py`):**
   - `POST /api/v1/wardrobe/items` (create from media asset).
   - `GET /api/v1/wardrobe/items` (filtered by category, color, formality, search).
   - `PATCH /api/v1/wardrobe/items/{id}` (logs user corrections to `item_label_corrections` for active learning).
   - `POST /api/v1/wardrobe/items/{id}/worn` (increments wear count).
   - `GET /api/v1/wardrobe/summary` (garment category statistics).

---

### Phase 4 — Body Analysis [P0 Manual, P1 Photo/Video]
1. **Manual Measurement Engine (P0):**
   - Process user inputs: shoulder, bust/chest, waist, hip, inseam, height.
   - Compute ratios: shoulder:hip, waist:hip, waist:shoulder, torso:leg.
   - Soft-rule classifier ([app/services/body/shape.py](file:///Users/inshrakhan/sih/stylesense/apps/api/app/services/body/shape.py)) evaluating canonical shapes against `data/body_rules.yaml` (Hourglass, Pear, Rectangle, Inverted Triangle, Apple).
   - Returns shape, confidence, runner-up, recommended silhouettes, and fit advice.
   - Store measurements encrypted (`body_profiles.measurements_enc`).
2. **Visual Pose & Landmark Pipeline (P1):**
   - MediaPipe Pose landmark extraction (shoulders, hips, knees, ankles) combined with person segmentation masks.
   - Automatic deletion of raw body photos/videos post-analysis by default.
3. **Endpoints (`app/routers/body.py`):**
   - `POST /api/v1/body/manual`: Input measurements.
   - `POST /api/v1/body/analyze`: Run visual analysis on uploaded media.
   - `GET /api/v1/body`: Retrieve shape styling guidance.
   - `PATCH /api/v1/body/correction`: Store user overrides (`user_corrected_shape`) for model calibration.

---

### Phase 5 — Outfit Engine v1 (Scored & Explainable) [P0]
1. **Garment Skeletons (`app/services/outfits/skeletons.py`):**
   - Define valid combinations: `top + bottom + shoes (+ layer) (+ bag)`, `dress + shoes`, and India-first `kurta/ethnic_set + bottom + dupatta + shoes`.
2. **Hard Constraints & Filtering:**
   - Availability check, occasion formality band compatibility, seasonal appropriateness, duplicate slot prevention.
3. **Multi-Factor Rule Scoring (`app/services/outfits/rules.py`):**
   - `body_fit` (silhouette harmony from body rules).
   - `color_harmony` ([app/services/outfits/color.py](file:///Users/inshrakhan/sih/stylesense/apps/api/app/services/outfits/color.py): complementary, analogous, monochromatic, neutral balancing in Lab/HCL color space).
   - `style_match` (user Style DNA match).
   - `occasion_match`, `season_match`, `layering_bonus`, `novelty` (penalize recently worn).
4. **Diversification & Variations:**
   - Top-N diversification via Maximal Marginal Relevance (MMR).
   - One-click variations: swap top, swap bottom, more formal, more casual, add one new catalog item.
5. **Grounded Explanations (`app/services/outfits/explain.py`):**
   - Template-based explanations highlighting top contributing score components ("Complements your pear silhouette", "Analogous earth tones").
6. **Endpoints (`app/routers/outfits.py`):**
   - `POST /api/v1/outfits/generate`, `POST /api/v1/outfits/{id}/variation`, `POST /api/v1/outfits/{id}/save`.

---

### Phase 6 — Catalog, Suggestions & Gap Analysis [P0 Local, P1 Live]
1. **Local Catalog Provider (`app/services/catalog/`):**
   - Seeded with ~200 diverse items (`catalog_seed.json`) in INR (₹) covering Indian and western styles.
   - Vector ANN search via `pgvector` indexed on catalog embeddings.
   - Non-scraping outbound deep-links to retailer searches (Myntra, Ajio, Amazon.in).
2. **Live Shopping Provider (P1):**
   - Permitted shopping API with 3-second timeout, rate limits, and automatic fallback to local catalog.
3. **Counterfactual Wardrobe Gap Analysis (`app/services/catalog/gaps.py`):**
   - Simulate virtual archetypes (e.g., "beige linen trousers", "white sneakers", "black kurta").
   - Compute how many new valid outfits are unlocked for the user's top occasions.
   - Rank gaps by utility: "Black trousers unlocks 4 college, 2 semi-formal outfits".
4. **Endpoints:** `GET /api/v1/gaps`, `GET /api/v1/suggestions`, `GET /api/v1/trends`, `POST /api/v1/wishlist`.

---

### Phase 7 — The Continuous Learning System (ML Core) [P0/P1]
1. **Event Ingestion:** Append-only logging of user interactions: `impression`, `like`, `dislike`, `save`, `skip`, `wear`, `buy_click` ([app/routers/outfits.py](file:///Users/inshrakhan/sih/stylesense/apps/api/app/routers/outfits.py)).
2. **Online Personalization (Style DNA):**
   - Instant EMA updates on `user_style_state.style_vector`:
     $$\text{style\_vector} \leftarrow (1-\eta)\cdot\text{style\_vector} + \eta\cdot\text{sign}\cdot\text{mean}(\text{item\_embeddings})$$
   - Real-time updates to style tag affinities (minimal, streetwear, ethnic, etc.).
3. **Learned Ranker:**
   - Cold start: Blended score $\alpha \cdot \text{rule\_score} + (1-\alpha) \cdot \text{model\_score}$.
   - Small event volume: Scikit-learn Logistic Regression.
   - Large event volume: LightGBM LambdaRank with Inverse Propensity Scoring (IPS) to eliminate position bias.
4. **Model Registry & Retraining (`train.py`, `evaluate.py`):**
   - Champion/Challenger evaluation on holdout NDCG@5 and per-body-shape slice metrics.
   - Promotion gating: Regressions on demographic/shape slices prevent deployment.
   - Synthetic bootstrap script (`scripts/bootstrap_synthetic.py`) using LLM-as-judge offline ratings.

---

### Phase 8 — Frontend Web Application [P0]
1. **Tech Stack:** Next.js (App Router), TypeScript strict mode, Tailwind CSS, shadcn/ui, TanStack Query.
2. **Client Architecture:** Strongly typed API client generated from FastAPI OpenAPI specification.
3. **Screens & Flows:**
   - Landing, Registration & Login.
   - Granular Consent Modal (body media, third-party AI, analytics).
   - Style Profile Stepper (occasions, colors, budget in ₹).
   - Body Analysis Screen (interactive silhouette adjustment & manual measurement entry).
   - Wardrobe Gallery (drag-and-drop photo/video uploads, category filters, review badges).
   - Outfit Recommendation Canvas (outfit cards, "Why this works", interactive like/dislike/save, variation toggles).
   - Wardrobe Gaps & Shop Hub (visual gap unlock counter, deep-link product cards).
   - Style DNA Dashboard (visual affinity bars).
   - Privacy & Account Center (export data zip, delete body media, delete account).

---

### Phase 9 — Seed & Demo Data [P0]
- Execute `scripts/seed_demo.py` creating:
  - Demo user (`demo@stylesense.ai`).
  - Pre-analyzed Pear shape body profile.
  - 25-item curated wardrobe with placeholder cutouts and vectors.
  - 200 catalog products and current fashion trends.
  - 50 pre-seeded user interactions ensuring Style DNA is visibly trained on first run.
- Single command execution: `make demo`.

---

### Phase 10 — Hardening, Compliance & Release [P0]
- Security scans: Bandit, pip-audit, npm audit, gitleaks validation.
- Resilience checks: Circuit breakers on LLM and external search APIs.
- Documentation completion:
  - `docs/THREAT_MODEL.md` (STRIDE-lite model).
  - `docs/PRIVACY.md` (data retention and encryption policies).
  - `docs/ML_CARD.md` (model limitations, fairness across skin tones, lighting, and body shapes).
  - `docs/API.md` (OpenAPI reference).

---

## 5. Immediate Next Steps for Implementation

1. **Implement Phase 2 Storage Service:** Create `app/services/storage/s3.py` (MinIO/S3) and `app/services/storage/localfs.py` implementing `StorageProvider`.
2. **Implement Media Validation & Upload Router:** Build `app/services/media/validate.py`, `app/services/media/sanitize.py`, and `app/routers/media.py` for streamed image/video ingestion.
3. **Set Up Background Worker:** Configure Arq worker tasks in `app/workers/tasks.py` for asynchronous media sanitization, thumbnail generation, and face blurring.
4. **Maintain Progress Checklists:** Keep [docs/PROGRESS.md](file:///Users/inshrakhan/sih/stylesense/docs/PROGRESS.md) and [docs/DECISIONS.md](file:///Users/inshrakhan/sih/stylesense/docs/DECISIONS.md) updated as each vertical slice is completed.
