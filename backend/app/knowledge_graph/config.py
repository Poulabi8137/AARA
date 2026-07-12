from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings


class KnowledgeGraphSettings(BaseSettings):
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

    class Config:
        env_prefix = "graph_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_knowledge_graph_settings() -> KnowledgeGraphSettings:
    return KnowledgeGraphSettings()
