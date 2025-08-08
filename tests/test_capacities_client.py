from unittest.mock import Mock, patch
from datetime import datetime

from readwise_twos_sync.capacities_client import CapacitiesClient


def test_post_highlights_sends_markdown():
    client = CapacitiesClient(token="token", space_id="space")

    highlights = [{"book_id": 1, "text": "Quote"}]
    books = {1: {"title": "Book", "author": "Author"}}

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None

    with patch("readwise_twos_sync.capacities_client.requests.post", return_value=mock_response) as mock_post:
        client.post_highlights(highlights, books)

        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        assert url == "https://api.capacities.io/save-to-daily-note"
        payload = mock_post.call_args[1]["json"]
        assert payload["spaceId"] == "space"
        assert payload["mdText"] == "- Quote — Book, Author"


def test_post_highlights_handles_empty_list():
    client = CapacitiesClient(token="token", space_id="space")

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None

    with patch("readwise_twos_sync.capacities_client.requests.post", return_value=mock_response) as mock_post:
        client.post_highlights([], {})

        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        assert payload["spaceId"] == "space"
        today = datetime.now().strftime("%Y-%m-%d")
        assert payload["mdText"] == f"No new highlights for {today}"
