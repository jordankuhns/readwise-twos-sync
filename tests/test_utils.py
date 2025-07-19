"""
Test utility functions and helpers
"""

import pytest
from datetime import datetime, timedelta
from backend.app import cipher_suite


class TestUtilities:
    """Test utility functions and encryption."""
    
    def test_encryption_decryption(self):
        """Test token encryption and decryption."""
        original_token = "test_api_token_12345"
        
        # Encrypt
        encrypted = cipher_suite.encrypt(original_token.encode())
        assert encrypted != original_token.encode()
        
        # Decrypt
        decrypted = cipher_suite.decrypt(encrypted).decode()
        assert decrypted == original_token
    
    def test_encryption_different_inputs(self):
        """Test that different inputs produce different encrypted outputs."""
        token1 = "token_one"
        token2 = "token_two"
        
        encrypted1 = cipher_suite.encrypt(token1.encode())
        encrypted2 = cipher_suite.encrypt(token2.encode())
        
        assert encrypted1 != encrypted2
    
    def test_sync_time_parsing(self):
        """Test sync time string parsing."""
        sync_time = "14:30"
        hour, minute = map(int, sync_time.split(':'))
        
        assert hour == 14
        assert minute == 30
    
    def test_sync_time_edge_cases(self):
        """Test edge cases for sync time parsing."""
        # Test midnight
        sync_time = "00:00"
        hour, minute = map(int, sync_time.split(':'))
        assert hour == 0
        assert minute == 0
        
        # Test late evening
        sync_time = "23:59"
        hour, minute = map(int, sync_time.split(':'))
        assert hour == 23
        assert minute == 59
    
    def test_days_back_calculation(self):
        """Test days back calculation for sync."""
        now = datetime.utcnow()
        days_back = 3
        
        since_time = now - timedelta(days=days_back)
        since_iso = since_time.isoformat()
        
        # Should be a valid ISO format
        assert 'T' in since_iso
        assert len(since_iso) > 10  # More than just date
        
        # Should be earlier than now
        assert since_time < now
    
    def test_highlight_filtering(self):
        """Test highlight filtering logic."""
        highlights = [
            {"id": 1, "updated": "2023-01-01T10:00:00Z", "text": "Test 1"},
            {"id": 2, "updated": "2023-01-02T10:00:00Z", "text": "Test 2"},
            {"id": 3, "updated": "2022-12-31T10:00:00Z", "text": "Test 3"},
        ]
        
        since = "2023-01-01T00:00:00Z"
        
        # Filter highlights updated since the given time
        filtered = [h for h in highlights if h.get("updated") and h["updated"] > since]
        
        assert len(filtered) == 2
        assert filtered[0]["id"] == 1
        assert filtered[1]["id"] == 2
    
    def test_book_metadata_handling(self):
        """Test book metadata processing."""
        books = {
            1: {"title": "Test Book", "author": "Test Author"},
            2: {"title": "Another Book", "author": "Another Author"}
        }
        
        highlight = {"book_id": 1, "text": "Great insight"}
        
        book_meta = books.get(highlight["book_id"])
        assert book_meta is not None
        assert book_meta["title"] == "Test Book"
        assert book_meta["author"] == "Test Author"
        
        # Test missing book
        highlight_missing = {"book_id": 999, "text": "Missing book"}
        book_meta_missing = books.get(highlight_missing["book_id"])
        assert book_meta_missing is None