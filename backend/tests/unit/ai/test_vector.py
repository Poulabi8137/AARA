from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.vector.client import QdrantClientWrapper, QdrantConfig
from app.ai.vector.collection_manager import CollectionConfig, CollectionManager
from app.ai.vector.search import SearchResultItem, VectorSearch


def _make_mock_response(is_success=True, json_data=None):
    resp = MagicMock()
    resp.is_success = is_success
    resp.json.return_value = json_data or {}
    return resp


def _make_mock_http_client():
    client = MagicMock()
    client.get = AsyncMock(return_value=_make_mock_response())
    client.put = AsyncMock(return_value=_make_mock_response())
    client.post = AsyncMock(return_value=_make_mock_response())
    client.delete = AsyncMock(return_value=_make_mock_response())
    client.aclose = AsyncMock()
    return client


class TestQdrantConfig:
    def test_defaults(self):
        config = QdrantConfig()
        assert config.url == "http://localhost:6333"
        assert config.api_key is None
        assert config.prefer_grpc is False
        assert config.timeout == 30

    def test_custom_values(self):
        config = QdrantConfig(
            url="https://qdrant.example.com",
            api_key="test-key-123",
            prefer_grpc=True,
            timeout=60,
        )
        assert config.url == "https://qdrant.example.com"
        assert config.api_key == "test-key-123"
        assert config.prefer_grpc is True
        assert config.timeout == 60

    def test_partial_override(self):
        config = QdrantConfig(api_key="key-only")
        assert config.url == "http://localhost:6333"
        assert config.api_key == "key-only"
        assert config.prefer_grpc is False


def _make_wrapper(mock_http_client=None):
    config = QdrantConfig()
    w = QdrantClientWrapper(config)
    w._client = mock_http_client or _make_mock_http_client()
    return w


class TestQdrantClientWrapper:
    @pytest.fixture
    def wrapper(self):
        return _make_wrapper()

    @pytest.fixture
    def wrapper_real(self):
        config = QdrantConfig()
        return QdrantClientWrapper(config)

    async def test_collection_exists_returns_true(self, wrapper):
        client = wrapper._client
        client.get.return_value = _make_mock_response(is_success=True)
        result = await wrapper.collection_exists("my_collection")
        assert result is True
        client.get.assert_awaited_once_with("/collections/my_collection")

    async def test_collection_exists_returns_false(self, wrapper):
        client = wrapper._client
        client.get.return_value = _make_mock_response(is_success=False)
        result = await wrapper.collection_exists("missing")
        assert result is False

    async def test_create_collection_success(self, wrapper):
        client = wrapper._client
        client.put.return_value = _make_mock_response(is_success=True)
        cfg = {"vectors": {"size": 384, "distance": "Cosine"}}
        result = await wrapper.create_collection("vecs", cfg)
        assert result is True
        client.put.assert_awaited_once_with("/collections/vecs", json=cfg)

    async def test_create_collection_failure(self, wrapper):
        client = wrapper._client
        client.put.return_value = _make_mock_response(is_success=False)
        result = await wrapper.create_collection("vecs", {})
        assert result is False

    async def test_delete_collection(self, wrapper):
        client = wrapper._client
        client.delete.return_value = _make_mock_response(is_success=True)
        result = await wrapper.delete_collection("old_coll")
        assert result is True
        client.delete.assert_awaited_once_with("/collections/old_coll")

    async def test_list_collections(self, wrapper):
        client = wrapper._client
        client.get.return_value = _make_mock_response(
            is_success=True,
            json_data={
                "result": {
                    "collections": [
                        {"name": "coll_a"},
                        {"name": "coll_b"},
                    ]
                }
            },
        )
        result = await wrapper.list_collections()
        assert result == ["coll_a", "coll_b"]
        client.get.assert_awaited_once_with("/collections")

    async def test_list_collections_empty(self, wrapper):
        client = wrapper._client
        client.get.return_value = _make_mock_response(
            is_success=True,
            json_data={"result": {"collections": []}},
        )
        result = await wrapper.list_collections()
        assert result == []

    async def test_upsert(self, wrapper):
        client = wrapper._client
        client.put.return_value = _make_mock_response(is_success=True)
        points = [{"id": "1", "vector": [0.1, 0.2]}]
        result = await wrapper.upsert("coll", points)
        assert result is True
        client.put.assert_awaited_once_with(
            "/collections/coll/points", json={"points": points}
        )

    async def test_search_default(self, wrapper):
        client = wrapper._client
        client.post.return_value = _make_mock_response(
            is_success=True,
            json_data={
                "result": [{"id": "a", "score": 0.95, "payload": {"text": "hello"}}]
            },
        )
        result = await wrapper.search("coll", [0.1, 0.2, 0.3])
        assert len(result) == 1
        assert result[0]["id"] == "a"
        client.post.assert_awaited_once()
        call_args = client.post.call_args
        assert call_args[0][0] == "/collections/coll/points/search"
        assert call_args[1]["json"]["vector"] == [0.1, 0.2, 0.3]
        assert call_args[1]["json"]["limit"] == 20

    async def test_search_with_all_params(self, wrapper):
        client = wrapper._client
        client.post.return_value = _make_mock_response(
            is_success=True, json_data={"result": []}
        )
        await wrapper.search(
            "coll", [1.0, 2.0], limit=5, score_threshold=0.7,
            query_filter={"must": [{"key": "k", "match": {"value": "v"}}]},
        )
        call_args = client.post.call_args
        payload = call_args[1]["json"]
        assert payload["limit"] == 5
        assert payload["score_threshold"] == 0.7
        assert payload["filter"] == {"must": [{"key": "k", "match": {"value": "v"}}]}

    async def test_search_raise_for_status(self, wrapper):
        client = wrapper._client
        client.post.return_value = _make_mock_response(is_success=True)
        client.post.return_value.raise_for_status.side_effect = Exception("HTTP error")
        with pytest.raises(Exception, match="HTTP error"):
            await wrapper.search("coll", [1.0])

    async def test_delete_points(self, wrapper):
        client = wrapper._client
        client.post.return_value = _make_mock_response(is_success=True)
        result = await wrapper.delete_points("coll", ["p1", "p2"])
        assert result is True
        client.post.assert_awaited_once_with(
            "/collections/coll/points/delete", json={"points": ["p1", "p2"]}
        )

    async def test_scroll_without_offset(self, wrapper):
        client = wrapper._client
        client.post.return_value = _make_mock_response(
            is_success=True,
            json_data={
                "result": {
                    "points": [{"id": "1", "payload": {"x": 1}}],
                    "next_page_offset": None,
                }
            },
        )
        points, offset = await wrapper.scroll("coll", limit=50)
        assert len(points) == 1
        assert offset is None
        client.post.assert_awaited_once_with(
            "/collections/coll/points/scroll",
            json={"limit": 50, "with_payload": True, "with_vector": False},
        )

    async def test_scroll_with_offset(self, wrapper):
        client = wrapper._client
        client.post.return_value = _make_mock_response(
            is_success=True,
            json_data={
                "result": {
                    "points": [{"id": "2"}],
                    "next_page_offset": "next_token",
                }
            },
        )
        points, offset = await wrapper.scroll("coll", limit=10, offset="abc")
        assert offset == "next_token"
        client.post.assert_awaited_once_with(
            "/collections/coll/points/scroll",
            json={"limit": 10, "offset": "abc", "with_payload": True, "with_vector": False},
        )

    async def test_count(self, wrapper):
        client = wrapper._client
        client.post.return_value = _make_mock_response(
            is_success=True,
            json_data={"result": {"count": 42}},
        )
        result = await wrapper.count("coll")
        assert result == 42
        client.post.assert_awaited_once_with(
            "/collections/coll/points/count", json={}
        )

    async def test_count_zero(self, wrapper):
        client = wrapper._client
        client.post.return_value = _make_mock_response(
            is_success=True,
            json_data={"result": {"count": 0}},
        )
        result = await wrapper.count("empty")
        assert result == 0

    async def test_close_none(self, wrapper_real):
        await wrapper_real.close()
        assert wrapper_real._client is None

    async def test_close_existing(self, wrapper_real):
        mock_client = _make_mock_http_client()
        wrapper_real._client = mock_client
        await wrapper_real.close()
        mock_client.aclose.assert_awaited_once()
        assert wrapper_real._client is None

    async def test_get_client_creates_once(self):
        config = QdrantConfig(api_key="sk-test")
        wrapper = QdrantClientWrapper(config)
        with patch("httpx.AsyncClient") as mock_httpx:
            client_a = await wrapper._get_client()
            client_b = await wrapper._get_client()
        assert client_a is client_b
        mock_httpx.assert_called_once_with(
            base_url="http://localhost:6333",
            headers={"Content-Type": "application/json", "api-key": "sk-test"},
            timeout=30,
        )

    async def test_update_points_delegates_to_upsert(self, wrapper):
        client = wrapper._client
        client.put.return_value = _make_mock_response(is_success=True)
        points = [{"id": "p1", "vector": [0.5]}]
        result = await wrapper.update_points("coll", points)
        assert result is True
        client.put.assert_awaited_once_with(
            "/collections/coll/points", json={"points": points}
        )


class TestCollectionConfig:
    def test_defaults(self):
        cfg = CollectionConfig()
        assert cfg.dimension == 384
        assert cfg.distance == "Cosine"
        assert cfg.payload_indexes == []

    def test_custom(self):
        indexes = [{"field_name": "author", "field_type": "keyword"}]
        cfg = CollectionConfig(dimension=768, distance="Euclid", payload_indexes=indexes)
        assert cfg.dimension == 768
        assert cfg.distance == "Euclid"
        assert cfg.payload_indexes == indexes


class TestCollectionManager:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock(spec_set=QdrantClientWrapper)

    @pytest.fixture
    def manager(self, mock_client):
        return CollectionManager(mock_client)

    async def test_ensure_collection_already_exists(self, manager, mock_client):
        mock_client.collection_exists.return_value = True
        result = await manager.ensure_collection("existing")
        assert result is True
        mock_client.collection_exists.assert_awaited_once_with("existing")
        mock_client.create_collection.assert_not_called()

    async def test_ensure_collection_creates(self, manager, mock_client):
        mock_client.collection_exists.return_value = False
        mock_client.create_collection.return_value = True
        mock_client._get_client = AsyncMock()

        result = await manager.ensure_collection("new_coll")
        assert result is True
        mock_client.create_collection.assert_awaited_once()
        call_args = mock_client.create_collection.call_args
        assert call_args[0][0] == "new_coll"
        cfg = call_args[0][1]
        assert cfg["vectors"]["size"] == 384
        assert cfg["vectors"]["distance"] == "Cosine"
        assert cfg["quantization_config"]["scalar"]["type"] == "int8"

    async def test_ensure_collection_with_custom_config(self, manager, mock_client):
        mock_client.collection_exists.return_value = False
        mock_client.create_collection.return_value = True
        mock_client._get_client = AsyncMock()

        custom = CollectionConfig(dimension=1536, distance="Dot", quantization=None)
        await manager.ensure_collection("custom", custom)
        call_args = mock_client.create_collection.call_args
        cfg = call_args[0][1]
        assert cfg["vectors"]["size"] == 1536
        assert cfg["vectors"]["distance"] == "Dot"
        assert "quantization_config" not in cfg

    async def test_ensure_collection_creates_payload_indexes(self, manager, mock_client):
        mock_client.collection_exists.return_value = False
        mock_client.create_collection.return_value = True
        mock_http = AsyncMock()
        mock_http.put = AsyncMock()
        mock_client._get_client = AsyncMock(return_value=mock_http)

        await manager.ensure_collection("idx_coll")
        assert mock_http.put.call_count >= 4

    async def test_ensure_collection_create_fails(self, manager, mock_client):
        mock_client.collection_exists.return_value = False
        mock_client.create_collection.return_value = False
        result = await manager.ensure_collection("fail")
        assert result is False

    async def test_delete_collection(self, manager, mock_client):
        mock_client.delete_collection.return_value = True
        result = await manager.delete_collection("del_me")
        assert result is True
        mock_client.delete_collection.assert_awaited_once_with("del_me")

    async def test_list_collections(self, manager, mock_client):
        mock_client.list_collections.return_value = ["a", "b"]
        result = await manager.list_collections()
        assert result == ["a", "b"]

    async def test_collection_info_found(self, manager, mock_client):
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "result": {"status": "green", "vectors_count": 100}
        }
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_client._get_client = AsyncMock(return_value=mock_http)
        info = await manager.collection_info("my_coll")
        assert info == {"status": "green", "vectors_count": 100}
        mock_http.get.assert_awaited_once_with("/collections/my_coll")

    async def test_collection_info_not_found(self, manager, mock_client):
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_client._get_client = AsyncMock(return_value=mock_http)
        info = await manager.collection_info("ghost")
        assert info is None

    def test_get_collection_name(self):
        name = CollectionManager.get_collection_name("sentence-transformers/all-MiniLM-L6-v2")
        assert name == "vectors_sentence_transformers_all_MiniLM_L6_v2"

    def test_get_collection_name_no_replace_needed(self):
        name = CollectionManager.get_collection_name("simple")
        assert name == "vectors_simple"


class TestSearchResultItem:
    def test_defaults(self):
        item = SearchResultItem(id="abc", score=0.5)
        assert item.id == "abc"
        assert item.score == 0.5
        assert item.payload == {}
        assert item.vector is None

    def test_full(self):
        item = SearchResultItem(
            id="xyz", score=0.99,
            payload={"text": "hello"}, vector=[0.1, 0.2],
        )
        assert item.vector == [0.1, 0.2]
        assert item.payload["text"] == "hello"

    def test_ordering(self):
        items = [
            SearchResultItem(id="a", score=0.3),
            SearchResultItem(id="b", score=0.9),
            SearchResultItem(id="c", score=0.6),
        ]
        sorted_items = sorted(items, key=lambda x: x.score, reverse=True)
        assert [i.id for i in sorted_items] == ["b", "c", "a"]


class TestVectorSearch:
    @pytest.fixture
    def mock_client(self):
        return AsyncMock(spec_set=QdrantClientWrapper)

    @pytest.fixture
    def vs(self, mock_client):
        return VectorSearch(mock_client)

    async def test_search_no_filters(self, vs, mock_client):
        mock_client.search.return_value = [
            {"id": "1", "score": 0.9, "payload": {"text": "doc1"}},
            {"id": "2", "score": 0.8, "payload": {"text": "doc2"}},
        ]
        results = await vs.search("coll", [1.0, 2.0])
        assert len(results) == 2
        assert isinstance(results[0], SearchResultItem)
        assert results[0].id == "1"
        assert results[0].score == 0.9
        assert results[0].payload == {"text": "doc1"}
        mock_client.search.assert_awaited_once_with(
            collection="coll", query_vector=[1.0, 2.0],
            limit=20, score_threshold=None, query_filter=None,
        )

    async def test_search_with_workspace_id(self, vs, mock_client):
        mock_client.search.return_value = []
        await vs.search("coll", [1.0], workspace_id="ws_1")
        expected_filter = {
            "must": [{"key": "workspace_id", "match": {"value": "ws_1"}}]
        }
        assert mock_client.search.call_args[1]["query_filter"] == expected_filter

    async def test_search_with_filter_kwargs(self, vs, mock_client):
        mock_client.search.return_value = []
        await vs.search(
            "coll", [1.0], workspace_id="ws_1",
            filter_kwargs={"author": "Smith", "year": "2024"},
        )
        call_filter = mock_client.search.call_args[1]["query_filter"]
        assert len(call_filter["must"]) == 3

    async def test_search_with_score_threshold(self, vs, mock_client):
        mock_client.search.return_value = []
        await vs.search("coll", [1.0], score_threshold=0.75)
        assert mock_client.search.call_args[1]["score_threshold"] == 0.75

    async def test_search_empty_results(self, vs, mock_client):
        mock_client.search.return_value = []
        results = await vs.search("coll", [1.0])
        assert results == []

    async def test_batch_insert_with_ids(self, vs, mock_client):
        mock_client.upsert.return_value = True
        result = await vs.batch_insert(
            collection="coll",
            vectors=[[0.1], [0.2]],
            payloads=[{"a": 1}, {"b": 2}],
            ids=["id1", "id2"],
        )
        assert result is True
        mock_client.upsert.assert_awaited_once()
        points = mock_client.upsert.call_args[0][1]
        assert points[0]["id"] == "id1"
        assert points[0]["vector"] == [0.1]
        assert points[0]["payload"] == {"a": 1}
        assert points[1]["id"] == "id2"

    async def test_batch_insert_auto_ids(self, vs, mock_client):
        mock_client.upsert.return_value = True
        result = await vs.batch_insert(
            collection="coll",
            vectors=[[0.3]],
            payloads=[{"x": "y"}],
        )
        assert result is True
        points = mock_client.upsert.call_args[0][1]
        assert isinstance(points[0]["id"], str)

    async def test_batch_insert_empty(self, vs, mock_client):
        mock_client.upsert.return_value = True
        result = await vs.batch_insert(
            collection="coll", vectors=[], payloads=[],
        )
        assert result is True
        points = mock_client.upsert.call_args[0][1]
        assert points == []

    async def test_delete(self, vs, mock_client):
        mock_client.delete_points.return_value = True
        result = await vs.delete("coll", ["p1", "p2", "p3"])
        assert result is True
        mock_client.delete_points.assert_awaited_once_with("coll", ["p1", "p2", "p3"])

    async def test_delete_empty(self, vs, mock_client):
        mock_client.delete_points.return_value = True
        result = await vs.delete("coll", [])
        assert result is True

    async def test_update_vector_and_payload(self, vs, mock_client):
        mock_client.update_points.return_value = True
        result = await vs.update("coll", "p1", vector=[0.5, 0.6], payload={"key": "val"})
        assert result is True
        mock_client.update_points.assert_awaited_once_with(
            "coll", [{"id": "p1", "vector": [0.5, 0.6], "payload": {"key": "val"}}]
        )

    async def test_update_vector_only(self, vs, mock_client):
        mock_client.update_points.return_value = True
        await vs.update("coll", "p1", vector=[1.0])
        mock_client.update_points.assert_awaited_once_with(
            "coll", [{"id": "p1", "vector": [1.0]}]
        )

    async def test_update_payload_only(self, vs, mock_client):
        mock_client.update_points.return_value = True
        await vs.update("coll", "p1", payload={"status": "done"})
        mock_client.update_points.assert_awaited_once_with(
            "coll", [{"id": "p1", "payload": {"status": "done"}}]
        )

    async def test_search_by_text(self, vs, mock_client):
        mock_client.search.return_value = [
            {"id": "1", "score": 0.95, "payload": {"content": "matched"}}
        ]
        mock_embedder = AsyncMock()
        mock_embedder.embed_query.return_value.vector = [0.1, 0.2, 0.3]

        results = await vs.search_by_text("coll", "hello world", mock_embedder)
        assert len(results) == 1
        mock_embedder.embed_query.assert_awaited_once_with("hello world")
        mock_client.search.assert_awaited_once_with(
            collection="coll", query_vector=[0.1, 0.2, 0.3],
            limit=20, score_threshold=None, query_filter=None,
        )
