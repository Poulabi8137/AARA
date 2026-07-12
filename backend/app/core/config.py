from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AARA API"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = (
        "postgresql+asyncpg://agentwatch:agentwatch@localhost:5432/agentwatch"
    )
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20

    secret_key: str = ""
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Security
    token_version: int = 1
    password_min_length: int = 8
    password_max_length: int = 128
    max_login_attempts: int = 5
    login_lockout_minutes: int = 15
    reset_token_expire_hours: int = 1
    require_email_verification: bool = False
    cors_allow_credentials: bool = True

    max_upload_size: int = 10 * 1024 * 1024  # 10 MB

    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    log_level: str = "INFO"
    log_format: str = "json"

    vectorstore_persist_dir: str = "./chroma_data"
    vectorstore_collection_count: int = 9
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_provider: str = "minilm"
    chroma_host: str = "localhost"
    chroma_port: str = "8001"

    # Research Memory Vector Store
    memory_indexing_enabled: bool = True
    memory_embedding_batch_size: int = 10
    memory_search_top_k: int = 10
    memory_collection_prefix: str = "memory_"

    # Research Memory Consolidation
    consolidation_enabled: bool = True
    consolidation_interval_minutes: int = 60
    consolidation_similarity_threshold: float = 0.85
    consolidation_min_confidence: float = 0.3
    consolidation_max_memories_per_group: int = 50
    consolidation_dry_run: bool = False

    # Memory Aging
    aging_active_ttl_days: int = 90
    aging_low_importance_ttl_days: int = 180
    aging_archive_ttl_days: int = 365
    aging_decay_factor: float = 0.05
    aging_archive_threshold: float = 0.2

    # Knowledge Evolution
    evolution_confidence_boost: float = 0.1
    evolution_upgrade_threshold: float = 0.6
    evolution_propagation_threshold: float = 0.85

    # RAG Core
    rag_retrieval_top_k: int = 10
    rag_retrieval_semantic_top_k: int = 10
    rag_retrieval_keyword_top_k: int = 10
    rag_retrieval_hybrid_weight: float = 0.7
    rag_retrieval_min_confidence: float = 0.3
    rag_retrieval_rerank_enabled: bool = True
    rag_retrieval_rerank_top_k: int = 5
    rag_retrieval_platform_top_k: int = 5
    rag_routing_default_strategy: str = "intent_based"
    rag_routing_keyword_boost: bool = True
    rag_ranking_semantic_weight: float = 0.5
    rag_ranking_source_weight: float = 0.2
    rag_ranking_freshness_weight: float = 0.15
    rag_ranking_confidence_weight: float = 0.15
    rag_ranking_freshness_decay_days: int = 365
    rag_citation_max_per_query: int = 5
    rag_citation_score_threshold: float = 0.5
    rag_context_max_tokens: int = 4096
    rag_context_deduplication_enabled: bool = True
    rag_response_max_tokens: int = 2048
    rag_response_temperature: float = 0.3
    rag_provider_model: str = "gpt-4o"
    rag_provider_timeout_seconds: int = 120

    llm_provider: str = "mock"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    openai_api_key: str = ""
    gemini_api_key: str = ""

    redis_url: str = "memory"
    redis_pool_size: int = 10
    redis_max_retries: int = 3
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    redis_health_check_interval: int = 30
    default_cache_ttl: int = 300
    redis_health_check_on_startup: bool = True

    workflow_max_retries: int = 3
    workflow_node_timeout: int = 120
    require_human_approval: bool = False
    database_migration_on_startup: bool = False

    # HTTPS and SSL Configuration
    trusted_hosts: list[str] = []
    trusted_proxy_hosts: list[str] = []
    ssl_cert_path: str = ""
    ssl_key_path: str = ""
    ssl_port: int = 443
    http_port: int = 80

    # Security Headers Configuration
    security_headers_enabled: bool = True
    xss_protection_enabled: bool = True
    frame_options_enabled: bool = True
    content_type_options_enabled: bool = True
    referrer_policy_enabled: bool = True
    content_security_policy: str = ""
    permissive_policy: str = ""

    # Proxy Configuration
    proxy_headers_enabled: bool = True
    forwarded_for_enabled: bool = True
    forwarded_proto_enabled: bool = True
    forwarded_host_enabled: bool = True
    forwarded_port_enabled: bool = True

    # Security Headers Override
    security_headers_override: bool = False

    # Research Planner
    planner_max_planning_depth: int = 5
    planner_max_task_count: int = 20
    planner_dependency_validation: bool = True
    planner_parallel_planning: bool = True
    planner_ambiguity_threshold: float = 0.4
    planner_confidence_threshold: float = 0.3
    planner_strategy_selection: str = "auto"
    planner_default_strategy: str = "general"
    planner_enable_memory_lookup: bool = True
    planner_version: str = "1.0"

    # Research Summarization
    summarization_default_level: str = "standard"
    summarization_max_summary_length: int = 4096
    summarization_default_grouping: str = "topic"
    summarization_citation_mode: str = "inline"
    summarization_confidence_threshold: float = 0.3
    summarization_max_findings: int = 10
    summarization_max_gaps: int = 5
    summarization_model: str = "gpt-4o"
    summarization_temperature: float = 0.3
    summarization_max_tokens: int = 2048

    # Research Analysis
    analysis_contradiction_threshold: float = 0.4
    analysis_consensus_threshold: float = 0.6
    analysis_trend_window_years: int = 3
    analysis_confidence_weights: str = "0.25,0.20,0.25,0.15,0.15"
    analysis_max_recommendations: int = 10
    analysis_max_contradictions: int = 10
    analysis_max_consensus: int = 15
    analysis_max_trends: int = 8
    analysis_max_limitations: int = 10
    analysis_max_relationships: int = 50
    analysis_relationship_confidence: float = 0.5
    analysis_model: str = "gpt-4o"
    analysis_temperature: float = 0.2

    # Research Methodology
    methodology_confidence_threshold: float = 0.3
    methodology_max_methods: int = 5
    methodology_max_datasets: int = 10
    methodology_max_benchmarks: int = 10
    methodology_max_risks: int = 10
    methodology_max_practices: int = 8
    methodology_evaluation_strictness: str = "standard"
    methodology_validation_strictness: str = "standard"
    methodology_risk_high_threshold: float = 0.7
    methodology_risk_medium_threshold: float = 0.4
    methodology_best_practice_mode: str = "standard"
    methodology_model: str = "gpt-4o"
    methodology_temperature: float = 0.2
    methodology_max_tokens: int = 2048
    methodology_enable_llm: bool = True
    methodology_max_warnings: int = 3

    # Research Experiment Planning
    experiment_hypothesis_confidence_threshold: float = 0.3
    experiment_complexity: str = "moderate"
    experiment_max_experiment_phases: int = 6
    experiment_max_experiment_steps: int = 30
    experiment_baseline_limits: int = 5
    experiment_benchmark_limits: int = 5
    experiment_evaluation_strictness: str = "standard"
    experiment_resource_estimation_mode: str = "auto"
    experiment_validation_strictness: str = "standard"
    experiment_max_hypotheses: int = 5
    experiment_max_variables: int = 15
    experiment_max_risks: int = 10
    experiment_temperature: float = 0.2
    experiment_max_tokens: int = 2048
    experiment_enable_llm: bool = True
    experiment_model: str = "gpt-4o"
    experiment_max_warnings: int = 3

    # Research Knowledge Graph
    graph_max_depth: int = 5
    graph_similarity_threshold: float = 0.7
    graph_confidence_decay: float = 0.85
    graph_max_neighbors: int = 50
    graph_enable_inference: bool = True
    graph_enable_provenance: bool = True
    graph_max_path_length: int = 10
    graph_validation_strictness: str = "standard"
    graph_relationship_threshold: float = 0.3
    graph_node_merge_threshold: float = 0.8
    graph_max_subgraph_size: int = 200
    graph_enable_incremental_updates: bool = True
    graph_max_orphan_ratio: float = 0.2
    graph_min_component_connectivity: float = 0.3
    graph_model: str = "gpt-4o"
    graph_temperature: float = 0.1
    graph_max_tokens: int = 1024
    graph_enable_llm: bool = True

    # Observability
    env: str = "development"
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
