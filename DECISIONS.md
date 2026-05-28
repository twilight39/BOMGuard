# BOMGuard — Engineering Decisions

This document records significant engineering decisions, the alternatives considered, and the rationale for each choice. It exists so that future maintainers (and interviewers) can understand why the system is built the way it is.

---

## Table of Contents

1. [ML: XGBoost over Neural Networks](#1-ml-xgboost-over-neural-networks)
2. [ML: Regulation-Agnostic Feature Pipeline](#2-ml-regulation-agnostic-feature-pipeline)
3. [ML: Temporal Split with Auto-Fallback](#3-ml-temporal-split-with-auto-fallback)
4. [ML: CalibratedClassifierCV over Raw XGBoost](#4-ml-calibratedclassifiercv-over-raw-xgboost)
5. [ML: Precision@Top100 as Primary Business Metric](#5-ml-precisiontop100-as-primary-business-metric)
6. [Data: Web Scraping over ECHA API](#6-data-web-scraping-over-echa-api)
7. [Data: PostgreSQL + pgvector over ChromaDB](#7-data-postgresql--pgvector-over-chromadb)
8. [LLM: Gemini 2.5 Flash over Local Ollama](#8-llm-gemini-25-flash-over-local-ollama)
9. [Embeddings: Gemini Text Embedding over sentence-transformers](#9-embeddings-gemini-text-embedding-over-sentence-transformers)
10. [Validator: Rule-Based over Isolation Forest](#10-validator-rule-based-over-isolation-forest)
11. [Container: Docker Compose over Kubernetes](#11-container-docker-compose-over-kubernetes)
12. [CI/CD: Blacksmith over GitHub-Hosted Runners](#12-cicd-blacksmith-over-github-hosted-runners)
13. [Reverse Proxy: Traefik over Nginx](#13-reverse-proxy-traefik-over-nginx)
14. [Frontend: Chart.js over Recharts](#14-frontend-chartjs-over-recharts)
15. [Real-Time: WebSockets over SSE](#15-real-time-websockets-over-sse)

---

## 1. ML: XGBoost over Neural Networks

**Decision**: Use XGBoost gradient boosted trees as the primary classifier for substance restriction risk prediction.

**Alternatives considered**:
- TabNet (neural network designed for tabular data)
- Simple MLP (multi-layer perceptron)
- Random Forest
- Logistic Regression

**Rationale**:
- XGBoost dominates tabular data benchmarks. With ~75 engineered features and ~23K training examples, the data regime firmly favors tree ensembles.
- Feature importance is natively extractable and directly interpretable via SHAP — compliance officers need to understand *why* a substance is flagged.
- No GPU required for training or inference. The 4GB Hetzner VPS handles training and serving without additional hardware.
- Hyperparameter optimization via Optuna is well-supported and converges reliably.
- Random Forest was evaluated as a baseline and achieved ~0.04 lower ROC-AUC on the same holdout set.

**Trade-off**: XGBoost does not capture non-linear feature interactions as flexibly as a deep network could. In practice, the regulation-specific Tanimoto similarity features are so strongly predictive that marginal gains from a neural architecture would not justify the added complexity.

---

## 2. ML: Regulation-Agnostic Feature Pipeline

**Decision**: Compute chemical features once per substance (universal), then add regulation-specific similarity features at model training and inference time.

**Alternative considered**: Train a single multi-label model that predicts restriction probability across all regulations simultaneously.

**Rationale**:
- Different regulators restrict substances for different reasons. REACH SVHC focuses on toxicity and bioaccumulation. PFAS restrictions target an entire chemical class regardless of individual toxicity profiles. A single model would blur these distinctions.
- Per-regulation models allow independent retraining, evaluation, and promotion. If the REACH model drifts, it can be retrained without affecting the PFAS model.
- The universal feature pipeline (RDKit fingerprints, EPA properties, molecular descriptors) is expensive to compute — it runs once per substance and is cached. Regulation-specific features (Tanimoto similarity to that regulation's restricted substances) are cheap to compute on demand.
- Adding a new regulation requires only a new set of labels and a model training run, not new feature engineering.

**Trade-off**: Memory overhead of loading multiple XGBoost models. With 2-3 active models this is negligible (~10MB each). At 10+ regulations, an ONNX-serving microservice may become warranted.

---

## 3. ML: Temporal Split with Auto-Fallback

**Decision**: Auto-switch between temporal holdout (train on older data, test on newer) and random stratified split based on available regulatory history length.

```python
# Auto-selection logic
def get_split_strategy(dates: pd.Series) -> tuple:
    n_batches = dates.dt.to_period('M').nunique()
    if n_batches >= 6:
        # Temporal: 80/20 split by date
        cutoff = dates.quantile(0.8)
        return 'temporal', dates < cutoff
    else:
        # Random stratified: preserves label distribution
        return 'random', stratified_split(dates)
```

**Alternatives considered**:
- Pure temporal split (always)
- Pure random stratified split (always)
- Walk-forward validation

**Rationale**:
- Temporal holdout is the gold standard for regulatory prediction — it simulates real deployment where you train on historical restrictions and predict future ones. However, it requires meaningful temporal depth.
- With fewer than 6 months of data, temporal splits produce unstable test sets (too few positive examples in the holdout). Random stratified preserves label distribution and gives a more reliable ROC-AUC estimate during early deployment.
- The strategy used is logged as an MLflow tag (`split_strategy`, `n_batches`), so evaluation context is preserved and auditable.
- After 6+ months of operation, the system automatically transitions to temporal splits as the data matures.

**Trade-off**: Random stratified can overestimate real-world performance because it does not test the model's ability to generalize to future regulatory patterns. This is acknowledged and documented — the metric target (ROC-AUC > 0.75) is set conservatively to account for this.

---

## 4. ML: CalibratedClassifierCV over Raw XGBoost

**Decision**: Apply Platt scaling (via scikit-learn's `CalibratedClassifierCV`) to raw XGBoost probability outputs.

**Alternative considered**: Use raw `predict_proba` outputs directly.

**Rationale**:
- Raw XGBoost probabilities are poorly calibrated — the model tends to push predictions toward 0 or 1 due to the boosting process. A substance with true 30% risk might output 80% probability.
- The dashboard displays risk tiers (Critical/High/Medium/Low) based on probability thresholds (0.80, 0.60, 0.30). Miscalibrated probabilities would place substances in the wrong tier.
- Calibration is essential for the Brier score metric target (< 0.10), which directly measures probability calibration quality.
- `CalibratedClassifierCV` with `cv=3` and `method='isotonic'` was chosen because the training set is small enough that isotonic regression does not overfit. With more data (>100K samples), Platt scaling (sigmoid) would be preferred.

**Trade-off**: Calibration adds a small runtime cost (~2ms per prediction). The model artifact is larger because the calibrator stores bin boundaries. Neither is material at this scale.

---

## 5. ML: Precision@Top100 as Primary Business Metric

**Decision**: Use Precision@Top100 (fraction of top-100 highest-risk predictions that are true positives) as the primary business-facing evaluation metric.

**Alternative considered**: ROC-AUC as the sole metric.

**Rationale**:
- ROC-AUC measures ranking quality but says nothing about the density of actionable predictions. A model can have high ROC-AUC while its top predictions are mostly false positives (common with severe class imbalance).
- Precision@Top100 directly answers the procurement question: "If I review the 100 substances your model flags as riskiest, how many will actually be restricted within 12 months?"
- This metric drives the UI design — the dashboard shows substances sorted by risk score, and procurement teams review from the top down.
- Target: > 0.15 (15 of the top 100 predictions are true positives). At this rate, a procurement team reviewing flagged substances catches 15 future restrictions proactively.

**Trade-off**: Precision@Top100 requires choosing a fixed k. k=100 is arbitrary but aligns with realistic procurement review bandwidth. The metric is logged alongside ROC-AUC and Average Precision for completeness.

---

## 6. Data: Web Scraping over ECHA API

**Decision**: Build a resilient web scraper for the ECHA Candidate List instead of using a REST API.

**Context**: ECHA does not provide a bulk REST API for substance data. The endpoint referenced in early project planning (`api.ec.europa.eu/documentation/echa`) does not exist.

**Rationale**:
- No official API exists. The only verified data access is via the public HTML table at `echa.europa.eu/candidate-list-table` and the ECHA CHEM web database.
- A production-grade scraper with content hashing, exponential backoff, and structured parsing demonstrates more practical engineering skill than calling an API. Hiring managers know that most real-world ML projects require data extraction from unstructured sources.
- The scraper is designed defensively: fallback selectors for HTML structure changes, local SQLite cache for offline operation, and SHA-256 content hashing to detect changes without re-parsing unchanged pages.
- IUCLID bulk downloads (~23,000 substances) are integrated as a quarterly manual import for the negative training labels.

**Trade-off**: Scraping is inherently fragile to website redesigns. Mitigation: the scraper uses multiple CSS selectors as fallbacks, and content hashing provides early warning if the page structure changes unexpectedly.

---

## 7. Data: PostgreSQL + pgvector over ChromaDB

**Decision**: Store LLM embeddings in PostgreSQL via the pgvector extension rather than using a dedicated vector database.

**Alternatives considered**:
- ChromaDB (dedicated vector store)
- Pinecone (managed vector database)
- Weaviate (self-hosted vector search engine)

**Rationale**:
- One less service to deploy, monitor, and backup. On a 4GB single-server setup, every eliminated service matters.
- Transactional consistency: regulatory summaries and their embeddings are written in a single INSERT/UPDATE. No risk of the summary and embedding diverging.
- Query patterns are simple — cosine similarity search with a LIMIT of 5. pgvector's ivfflat index handles this efficiently at the current scale (~300 regulatory summaries).
- If the project scales beyond ~100K vectors, ChromaDB or Pinecone can be introduced as a drop-in replacement — the embedding interface is standardized (768-dim float arrays).

**Trade-off**: pgvector's query performance degrades beyond ~100K vectors without careful index tuning (lists parameter). At that scale, a dedicated vector database becomes warranted. Current scale: ~300 vectors. Headroom: ~300x before migration needed.

---

## 8. LLM: Gemini 2.5 Flash over Local Ollama

**Decision**: Use Google's Gemini 2.5 Flash API for LLM inference rather than self-hosting Llama via Ollama.

**Context**: The deployment target is a Hetzner CX21 VPS with 2 vCPU and 4GB RAM.

**Rationale**:
- Ollama running Llama 3.1 8B requires ~6GB RAM at minimum for acceptable performance. The 4GB VPS cannot run it without aggressive swapping that would degrade the entire system.
- Gemini 2.5 Flash is the cheapest capable model available: ~$0.30/1M input tokens, high quality for summarization and Q&A, low latency.
- Estimated monthly cost for the project's usage: $0.50-2.00 (300 substance summaries + ~100 chat queries).
- The API client is wrapped behind a service interface. Swapping to a different provider (OpenAI GPT-4o-mini, Anthropic Claude Haiku, or a future self-hosted model) requires changing only the model name and API key — no architectural changes.

**Trade-off**: Ongoing API cost vs zero marginal cost for local inference. At $2/month, the cost is negligible compared to the VPS itself. Network dependency: if the Gemini API is unavailable, the RAG system falls back to keyword-based retrieval (already implemented as a degradation path).

---

## 9. Embeddings: Gemini Text Embedding over sentence-transformers

**Decision**: Use Google's Text Embedding API (`models/text-embedding-004`, 768-dim) instead of local sentence-transformers.

**Alternative considered**: `all-MiniLM-L6-v2` via sentence-transformers (local, free, 384-dim).

**Rationale**:
- Same API key as the LLM — no additional credential management.
- 768-dimensional embeddings capture more semantic nuance than 384-dim MiniLM. Regulatory text is domain-specific and dense; higher dimensionality improves retrieval accuracy for complex queries.
- Cost is negligible: embedding 300 substance summaries costs less than $0.01. Embedding a user query costs ~$0.0001.
- The embedding dimension (768) is fixed in the database schema. Switching to a different embedding model with a different dimension would require a schema migration. This is a known constraint documented here.

**Trade-off**: Network latency per embedding call (~50-100ms). Mitigated by caching: substance summaries are embedded once and stored. Only user queries require real-time embedding.

---

## 10. Validator: Rule-Based over Isolation Forest

**Decision**: Replace the originally planned Isolation Forest anomaly detection with a rule-based declaration validator.

**Context**: The original design proposed training an Isolation Forest on 1,000 synthetic supplier declarations with 5% injected anomalies. This creates a circularity problem: the data is synthetic, the anomalies are injected, and the evaluation measures detection of known-injected patterns.

**Rationale**:
- Real supplier declarations are private documents. No public dataset of material declarations exists for training.
- A rule-based validator using actual regulatory substance lists (ECHA SVHC, RoHS restricted) provides genuine, verifiable validation. The rules are grounded in real regulatory data, not synthetic patterns.
- The validator checks: restricted substance presence, SVHC status, concentration format validity, certificate expiry, and declaration completeness against IPC-1752A standards. These are exactly the checks compliance officers perform manually.
- The validator is extensible: new rules are added as new methods on the `DeclarationValidator` class, following the same plugin pattern as regulation adapters.

**Trade-off**: Rules require manual engineering for each new validation type. An ML-based approach could potentially discover novel anomaly patterns. In practice, regulatory compliance is rule-driven by nature — the rules *are* the ground truth.

---

## 11. Container: Docker Compose over Kubernetes

**Decision**: Use Docker Compose for production deployment rather than Kubernetes.

**Context**: Single Hetzner VPS (2 vCPU, 4GB RAM) running the full stack.

**Rationale**:
- Kubernetes control plane components (etcd, kube-apiserver, scheduler) consume ~1GB RAM alone. There would be no resources left for the actual application.
- Docker Compose provides sufficient orchestration for a single-node deployment: service dependencies, restart policies, volume mounts, environment variable injection.
- The `docker-compose.yml` is the production deployment artifact — no separate staging configuration. This eliminates environment drift.
- Kubernetes manifests are included in `k8s/` as documentation of the scale-out path, useful for interview discussions.

**Trade-off**: No horizontal pod autoscaling, no rolling updates with zero downtime, no built-in service discovery. Mitigation: Traefik handles health-check-based routing, and `docker compose up -d` restarts containers with ~5s downtime — acceptable for a portfolio demo.

---

## 12. CI/CD: Blacksmith over GitHub-Hosted Runners

**Decision**: Use Blacksmith runners (`blacksmith-4vcpu-ubuntu-2204`) instead of GitHub-hosted `ubuntu-latest`.

**Alternatives considered**:
- GitHub-hosted runners (free for public repos, $0.008/minute for private)
- Self-hosted runner on the Hetzner VPS

**Rationale**:
- Blacksmith is ~2x faster than GitHub-hosted runners for the same vCPU count, due to NVMe storage and optimized networking.
- 50% cheaper per minute than GitHub-hosted runners ($0.004/min vs $0.008/min). For a public open-source repo, both are free — but the speed improvement is meaningful.
- One-line change in workflow YAML: `runs-on: blacksmith-4vcpu-ubuntu-2204`. Standard GHA syntax is preserved — no lock-in.
- Using a novel CI provider demonstrates awareness of the CI/CD tooling landscape — a conversation starter in interviews.

**Trade-off**: Blacksmith is a newer provider with less ecosystem maturity than GitHub Actions. If they discontinue the service, reverting to GitHub-hosted runners is a single-line change.

---

## 13. Reverse Proxy: Traefik over Nginx

**Decision**: Use Traefik v3 as the edge reverse proxy instead of Nginx.

**Rationale**:
- Automatic Let's Encrypt certificate provisioning and renewal via Docker labels — no Certbot cron jobs, no manual certificate management.
- Native Docker provider: services are discovered automatically from container labels. Adding a new service requires only a label, no config file editing.
- Middleware stack (rate limiting, compression, CORS) is configured via labels, keeping configuration co-located with the service definition.
- Lower configuration boilerplate than Nginx for a containerized deployment.

**Trade-off**: Nginx has broader community knowledge and more battle-tested performance at extreme scale. Traefik's configuration language (labels) is less explicit than Nginx's config file format. At this scale, the difference is immaterial.

---

## 14. Frontend: Chart.js over Recharts

**Decision**: Use Chart.js 4 with react-chartjs-2 wrappers instead of Recharts.

**Rationale**:
- Chart.js is more widely known and documented. Hiring managers reviewing the codebase are more likely to recognize it.
- Better performance with large datasets (the regulatory history chart may display 250+ data points).
- More chart types available out of the box (the forecast visualization may require a combination chart).
- react-chartjs-2 provides clean React integration with minimal wrapper overhead.

**Trade-off**: Recharts is more "React-native" in its API design (declarative components vs. Chart.js's imperative config object). Chart.js requires a ref/canvas approach that is slightly less idiomatic in React. The difference is minor for the chart types used in this project.

---

## 15. Real-Time: WebSockets over SSE

**Decision**: Use WebSockets (FastAPI native via `starlette.websockets`) for real-time features instead of Server-Sent Events.

**Context**: Two real-time features exist: regulatory change alerts and LLM chat streaming.

**Rationale**:
- The LLM chat requires bidirectional communication (client sends question, server streams response). SSE is server-to-client only and would require a separate HTTP POST for the question, adding latency and complexity.
- A single WebSocket connection per client handles both chat and regulatory alerts, simplifying the connection management logic.
- FastAPI has first-class WebSocket support with the same dependency injection system as HTTP endpoints.

**Trade-off**: WebSockets are harder to load-balance and debug than SSE. Connection state must be managed (reconnection logic on the client). The project uses a single server, so load balancing is not a concern. Reconnection is handled by the React hook layer.
