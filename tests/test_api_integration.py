"""
Test API integration with external services
"""

import pytest
import json
from unittest.mock import patch, Mock
from datetime import datetime
from backend.app import perform_sync


class TestAPIIntegration:
    """Test integration with Readwise, Twos, and Capacities APIs."""
    
    @patch('requests.get')
    @patch('requests.post')
    def test_perform_sync_success(self, mock_post, mock_get):
        """Test successful sync operation."""
        # Mock Readwise API responses
        now = datetime.utcnow().isoformat() + "Z"
        mock_highlights_response = Mock()
        mock_highlights_response.raise_for_status.return_value = None
        mock_highlights_response.json.return_value = {
            "results": [
                {
                    "id": 1,
                    "text": "Test highlight 1",
                    "book_id": 1,
                    "updated": now
                },
                {
                    "id": 2,
                    "text": "Test highlight 2",
                    "book_id": 2,
                    "updated": now
                }
            ],
            "next": None
        }
        
        mock_books_response = Mock()
        mock_books_response.raise_for_status.return_value = None
        mock_books_response.json.return_value = {
            "results": [
                {"id": 1, "title": "Test Book 1", "author": "Test Author 1"},
                {"id": 2, "title": "Test Book 2", "author": "Test Author 2"}
            ],
            "next": None
        }
        
        def get_side_effect(url, **kwargs):
            if 'highlights' in url:
                return mock_highlights_response
            elif 'books' in url:
                return mock_books_response
            return Mock()
        
        mock_get.side_effect = get_side_effect
        
        # Mock Twos API response
        mock_twos_response = Mock()
        mock_twos_response.raise_for_status.return_value = None
        mock_twos_response.status_code = 200
        mock_post.return_value = mock_twos_response
        
        # Perform sync
        result = perform_sync(
            readwise_token='test_readwise_token',
            twos_user_id='test_twos_user',
            twos_token='test_twos_token',
            capacities_token='cap_token',
            capacities_space_id='space123',
            capacities_structure_id='struct123',
            capacities_text_property_id='textprop123',
            days_back=1
        )
        
        # Verify result
        assert result['success'] is True
        assert result['highlights_synced'] == 2
        assert 'Successfully synced' in result['message']
        
        # Verify API calls were made
        assert mock_get.call_count >= 2  # At least highlights and books calls
        assert mock_post.call_count == 4  # Two highlights to Twos and two to Capacities
    
    @patch('requests.get')
    def test_readwise_api_error(self, mock_get):
        """Test handling of Readwise API errors."""
        # Mock API error
        mock_get.side_effect = Exception("Readwise API error")
        
        # Perform sync and expect it to raise an exception
        with pytest.raises(Exception) as exc_info:
            perform_sync(
                readwise_token='test_readwise_token',
                twos_user_id='test_twos_user',
                twos_token='test_twos_token',
                capacities_token='cap_token',
                capacities_space_id='space123',
                capacities_structure_id='struct123',
                capacities_text_property_id='textprop123',
                days_back=1
            )
        
        assert "Readwise API error" in str(exc_info.value)
    
    @patch('requests.get')
    @patch('requests.post')
    def test_twos_api_error(self, mock_post, mock_get):
        """Test handling of Twos API errors."""
        # Mock successful Readwise responses
        mock_highlights_response = Mock()
        mock_highlights_response.raise_for_status.return_value = None
        now = datetime.utcnow().isoformat() + "Z"
        mock_highlights_response.json.return_value = {
            "results": [{"id": 1, "text": "Test", "book_id": 1, "updated": now}],
            "next": None
        }
        
        mock_books_response = Mock()
        mock_books_response.raise_for_status.return_value = None
        mock_books_response.json.return_value = {
            "results": [{"id": 1, "title": "Test Book", "author": "Test Author"}],
            "next": None
        }
        
        def get_side_effect(url, **kwargs):
            if 'highlights' in url:
                return mock_highlights_response
            elif 'books' in url:
                return mock_books_response
        
        mock_get.side_effect = get_side_effect
        
        # Mock Twos API error
        mock_post.side_effect = Exception("Twos API error")
        
        # Perform sync and expect it to raise an exception
        with pytest.raises(Exception):
            perform_sync(
                readwise_token='test_readwise_token',
                twos_user_id='test_twos_user',
                twos_token='test_twos_token',
                days_back=1,
                user_id=1
            )
    
    @patch('requests.get')
    @patch('requests.post')
    def test_no_highlights_found(self, mock_post, mock_get):
        """Test sync when no new highlights are found."""
        # Mock empty Readwise response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "results": [],
            "next": None
        }
        mock_get.return_value = mock_response
        
        # Mock Twos API response
        mock_twos_response = Mock()
        mock_twos_response.raise_for_status.return_value = None
        mock_twos_response.status_code = 200
        mock_post.return_value = mock_twos_response
        
        # Perform sync
        result = perform_sync(
            readwise_token='test_readwise_token',
            twos_user_id='test_twos_user',
            twos_token='test_twos_token',
            capacities_token='cap_token',
            capacities_space_id='space123',
            capacities_structure_id='struct123',
            capacities_text_property_id='textprop123',
            days_back=1
        )
        
        # Verify result
        assert result['success'] is True
        assert result['highlights_synced'] == 0
        assert 'No new highlights' in result['message']
        
        # Should still post to Twos (no highlights message)
        assert mock_post.call_count == 2
    
    def test_invalid_sync_parameters(self):
        """Test sync with invalid parameters."""
        with pytest.raises(Exception):
            perform_sync(
                readwise_token='',  # Empty token
                twos_user_id='test_user',
                twos_token='test_token',
                capacities_token='cap_token',
                capacities_space_id='space123',
                capacities_structure_id='struct123',
                capacities_text_property_id='textprop123',
                days_back=1
            )


