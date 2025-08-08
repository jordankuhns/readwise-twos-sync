import pytest
from unittest.mock import patch, Mock

from readwise_twos_sync.capacities_client import CapacitiesClient


def test_post_highlights_with_structure_and_properties():
    """Ensure highlights are posted with structure and properties."""
    client = CapacitiesClient(
        token="token",
        space_id="space",
        structure_id="root123",
        property_definition_ids={"text": "textProp", "title": "titleProp", "author": "authorProp"},
    )

    highlights = [{"book_id": 1, "text": "Quote"}]
    books = {1: {"title": "Book", "author": "Author"}}

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None

    with patch("readwise_twos_sync.capacities_client.requests.post", return_value=mock_response) as mock_post:
        client.post_highlights(highlights, books)

        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        assert url == "https://api.capacities.io/spaces/space/objects"
        payload = mock_post.call_args[1]["json"]
        assert payload["structureId"] == "root123"
        props = payload["properties"]
        assert props["textProp"] == "Quote"
        assert props["titleProp"] == "Book"
        assert props["authorProp"] == "Author"


def test_post_highlights_fetches_space_info_when_missing():
    """Client fetches structure and property IDs when not provided."""
    client = CapacitiesClient(token="token", space_id="space")

    highlights = [{"book_id": 1, "text": "Quote"}]
    books = {1: {"title": "Book", "author": "Author"}}

    mock_post_response = Mock()
    mock_post_response.raise_for_status.return_value = None

    mock_get_response = Mock()
    mock_get_response.raise_for_status.return_value = None
    mock_get_response.json.return_value = {
        "structures": [{"id": "root123", "name": "RootPage"}],
        "propertyDefinitions": [
            {"id": "textProp", "name": "text"},
            {"id": "titleProp", "name": "title"},
            {"id": "authorProp", "name": "author"},
        ],
    }

    with patch("readwise_twos_sync.capacities_client.requests.get", return_value=mock_get_response) as mock_get, \
        patch("readwise_twos_sync.capacities_client.requests.post", return_value=mock_post_response) as mock_post:
        client.post_highlights(highlights, books)

        mock_get.assert_called_once()
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert payload["structureId"] == "root123"
        props = payload["properties"]
        assert props["textProp"] == "Quote"
        assert props["titleProp"] == "Book"
        assert props["authorProp"] == "Author"
