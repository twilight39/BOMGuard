"""Prometheus counters and gauges for BOMGuard business metrics."""

from prometheus_client import Counter

bom_uploads_total = Counter(
    "bomguard_bom_uploads_total",
    "Total number of BOM uploads",
    ["source"],
)

scans_total = Counter(
    "bomguard_scans_total",
    "Total number of compliance scans run",
    ["status"],
)

llm_queries_total = Counter(
    "bomguard_llm_queries_total",
    "Total number of LLM / RAG queries",
    ["type"],
)

embeddings_generated_total = Counter(
    "bomguard_embeddings_generated_total",
    "Total number of embedding vectors generated",
)
