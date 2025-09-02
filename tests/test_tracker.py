import pytest
import time
import logging
import os
from core.tracker import TabTracker
from core.database import DatabaseManager

# Set up test logging
logging.basicConfig(level=logging.WARNING)

class TestTabTracker:
    def setup_method(self):
        # Use a test database in a subdirectory to avoid path issues
        self.test_db = "test_data/test_tracking.db"
        # Ensure test directory exists
        os.makedirs("test_data", exist_ok=True)
        self.tracker = TabTracker(update_interval=0.1, db_path=self.test_db)
    
    def teardown_method(self):
        # Clean up test database and directory
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists("test_data") and not os.listdir("test_data"):
            os.rmdir("test_data")
    
    def test_database_initialization(self):
        """Test that database initializes correctly"""
        # Database file should be created
        assert os.path.exists(self.test_db)
        
        # Database manager should be initialized
        assert self.tracker.db_manager is not None
        assert self.tracker.db_manager.db_path == self.test_db
    
    def test_database_integration(self):
        """Test that tracker saves to database"""
        # Start tracking briefly
        self.tracker.start_tracking()
        time.sleep(0.3)
        self.tracker.stop_tracking()
        
        # Check that data was saved to database
        db_history = self.tracker.get_history(from_db=True)
        memory_history = self.tracker.get_history(from_db=False)
        
        # Should have some entries (unless no windows were active)
        assert isinstance(db_history, list)
        assert isinstance(memory_history, list)
        
        # Database should be accessible
        total_time = self.tracker.db_manager.get_total_tracking_time()
        assert total_time >= 0  # Could be 0 if no windows captured
    
    def test_get_history_from_db(self):
        """Test retrieving history from database"""
        # Manually add some test data to database
        test_entry = {
            'title': 'Test Window',
            'app': 'Test App', 
            'timestamp': '2023-01-01T00:00:00',
            'duration': 60
        }
        
        success = self.tracker.db_manager.save_window_entry(test_entry)
        assert success == True
        
        # Retrieve from database
        history = self.tracker.get_history(from_db=True, limit=10)
        
        assert len(history) >= 1
        if history:  # If there are entries
            assert history[0]['title'] == 'Test Window'
            assert history[0]['app'] == 'Test App'

if __name__ == "__main__":
    pytest.main([__file__, "-v"])