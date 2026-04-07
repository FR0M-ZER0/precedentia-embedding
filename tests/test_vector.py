import pytest
from unittest.mock import MagicMock
from qdrant_client.models import PointStruct

from src.core.vector import vectorize, vectorize_entries


@pytest.fixture
def sample_value():
    return {
        "name": "Habeas Corpus",
        "description": "Protects individual freedom against unlawful detention.",
        "tribunal": "STF",
        "situation": "active",
        "url": "https://example.com/precedent/42",
    }


@pytest.fixture
def mock_model():
    model = MagicMock()
    model.encode.return_value = MagicMock(
        tolist=MagicMock(return_value=[0.1, 0.2, 0.3])
    )
    return model


@pytest.fixture
def mock_redis():
    client = MagicMock()
    return client


@pytest.fixture
def mock_qdrant():
    client = MagicMock()
    return client


class TestVectorize:
    def test_returns_correct_point_id(self, mock_model, sample_value):
        point_id, _, _ = vectorize(mock_model, "precedent:42", sample_value)
        assert point_id == 42

    def test_returns_vector_as_list(self, mock_model, sample_value):
        _, vector, _ = vectorize(mock_model, "precedent:42", sample_value)
        assert isinstance(vector, list)
        assert vector == [0.1, 0.2, 0.3]

    def test_encodes_name_and_description(self, mock_model, sample_value):
        vectorize(mock_model, "precedent:42", sample_value)
        expected_text = f"{sample_value['name']}. {sample_value['description']}"
        mock_model.encode.assert_called_once_with(expected_text)

    def test_payload_contains_all_expected_fields(self, mock_model, sample_value):
        _, _, payload = vectorize(mock_model, "precedent:42", sample_value)
        assert payload["name"] == sample_value["name"]
        assert payload["description"] == sample_value["description"]
        assert payload["tribunal"] == sample_value["tribunal"]
        assert payload["situation"] == sample_value["situation"]
        assert payload["url"] == sample_value["url"]

    def test_payload_has_no_extra_fields(self, mock_model, sample_value):
        _, _, payload = vectorize(mock_model, "precedent:42", sample_value)
        assert set(payload.keys()) == {
            "name",
            "description",
            "tribunal",
            "situation",
            "url",
        }

    def test_point_id_parsed_from_key(self, mock_model, sample_value):
        point_id, _, _ = vectorize(mock_model, "precedent:999", sample_value)
        assert point_id == 999

    def test_missing_optional_fields_default_to_none(self, mock_model):
        incomplete_value = {"name": "Test", "description": "Desc"}
        _, _, payload = vectorize(mock_model, "precedent:1", incomplete_value)
        assert payload["tribunal"] is None
        assert payload["situation"] is None
        assert payload["url"] is None

    def test_missing_name_uses_none_in_text(self, mock_model):
        value = {"description": "Only description"}
        vectorize(mock_model, "precedent:1", value)
        mock_model.encode.assert_called_once_with("None. Only description")

    def test_missing_description_uses_none_in_text(self, mock_model):
        value = {"name": "Only name"}
        vectorize(mock_model, "precedent:1", value)
        mock_model.encode.assert_called_once_with("Only name. None")


class TestVectorizeEntries:
    def test_upsert_called_once(
        self, mock_redis, mock_qdrant, mock_model, sample_value
    ):
        mock_redis.scan.return_value = (0, ["precedent:1"])
        mock_redis.hgetall.return_value = sample_value

        vectorize_entries(mock_redis, mock_qdrant, "precedents", mock_model)

        mock_qdrant.upsert.assert_called_once()

    def test_upsert_collection_name(
        self, mock_redis, mock_qdrant, mock_model, sample_value
    ):
        mock_redis.scan.return_value = (0, ["precedent:1"])
        mock_redis.hgetall.return_value = sample_value

        vectorize_entries(mock_redis, mock_qdrant, "my_collection", mock_model)

        _, kwargs = mock_qdrant.upsert.call_args
        assert kwargs["collection_name"] == "my_collection"

    def test_upsert_receives_correct_number_of_points(
        self, mock_redis, mock_qdrant, mock_model, sample_value
    ):
        keys = ["precedent:1", "precedent:2", "precedent:3"]
        mock_redis.scan.return_value = (0, keys)
        mock_redis.hgetall.return_value = sample_value

        vectorize_entries(mock_redis, mock_qdrant, "precedents", mock_model)

        _, kwargs = mock_qdrant.upsert.call_args
        assert len(kwargs["points"]) == 3

    def test_points_are_pointstruct_instances(
        self, mock_redis, mock_qdrant, mock_model, sample_value
    ):
        mock_redis.scan.return_value = (0, ["precedent:10"])
        mock_redis.hgetall.return_value = sample_value

        vectorize_entries(mock_redis, mock_qdrant, "precedents", mock_model)

        _, kwargs = mock_qdrant.upsert.call_args
        for point in kwargs["points"]:
            assert isinstance(point, PointStruct)

    def test_point_ids_match_keys(
        self, mock_redis, mock_qdrant, mock_model, sample_value
    ):
        mock_redis.scan.return_value = (0, ["precedent:7", "precedent:42"])
        mock_redis.hgetall.return_value = sample_value

        vectorize_entries(mock_redis, mock_qdrant, "precedents", mock_model)

        _, kwargs = mock_qdrant.upsert.call_args
        ids = {p.id for p in kwargs["points"]}
        assert ids == {7, 42}

    def test_scan_pagination_multiple_pages(
        self, mock_redis, mock_qdrant, mock_model, sample_value
    ):
        mock_redis.scan.side_effect = [
            (1, ["precedent:1"]),
            (2, ["precedent:2"]),
            (0, ["precedent:3"]),
        ]
        mock_redis.hgetall.return_value = sample_value

        vectorize_entries(mock_redis, mock_qdrant, "precedents", mock_model)

        assert mock_redis.scan.call_count == 3
        _, kwargs = mock_qdrant.upsert.call_args
        assert len(kwargs["points"]) == 3

    def test_empty_redis_upserts_empty_list(self, mock_redis, mock_qdrant, mock_model):
        mock_redis.scan.return_value = (0, [])

        vectorize_entries(mock_redis, mock_qdrant, "precedents", mock_model)

        mock_qdrant.upsert.assert_called_once()
        _, kwargs = mock_qdrant.upsert.call_args
        assert kwargs["points"] == []

    def test_scan_uses_correct_match_pattern(
        self, mock_redis, mock_qdrant, mock_model, sample_value
    ):
        mock_redis.scan.return_value = (0, ["precedent:1"])
        mock_redis.hgetall.return_value = sample_value

        vectorize_entries(mock_redis, mock_qdrant, "precedents", mock_model)

        first_call_kwargs = mock_redis.scan.call_args_list[0]
        assert first_call_kwargs.kwargs.get("match") == "precedent:*"

    def test_hgetall_called_for_each_key(
        self, mock_redis, mock_qdrant, mock_model, sample_value
    ):
        keys = ["precedent:1", "precedent:2"]
        mock_redis.scan.return_value = (0, keys)
        mock_redis.hgetall.return_value = sample_value

        vectorize_entries(mock_redis, mock_qdrant, "precedents", mock_model)

        assert mock_redis.hgetall.call_count == 2
        mock_redis.hgetall.assert_any_call("precedent:1")
        mock_redis.hgetall.assert_any_call("precedent:2")
