#!/usr/bin/env python3
"""
Tests for the file preprocessor
"""

import pytest
from pathlib import Path
from file_preprocessor import FilePreprocessor, FileContext


class TestFilePreprocessor:
    """Test the file preprocessor functionality"""
    
    @pytest.fixture
    def preprocessor(self):
        return FilePreprocessor()
    
    def test_python_preprocessing(self, preprocessor):
        """Test Python file preprocessing"""
        content = '''
import os
import json
from typing import List, Dict
from .local_module import helper

class DataProcessor:
    """Process data files"""
    
    def __init__(self):
        self.api_key = os.environ.get('API_KEY')
        self.base_url = "https://api.example.com/v1"
        
    def process_file(self, file_path: str) -> Dict:
        """Process a single file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # TODO: Add validation logic
        # FIXME: Handle large files better
        
        return self.transform_data(data)
    
    def transform_data(self, data: Dict) -> Dict:
        """Transform the data"""
        pass

def main():
    processor = DataProcessor()
    processor.process_file("data.json")

if __name__ == "__main__":
    main()
'''
        
        context = preprocessor.preprocess_file(Path("test.py"), content)
        
        assert context.language == "python"
        assert context.file_type == "source"
        assert "os" in context.imports
        assert "json" in context.imports
        assert "typing" in context.imports
        assert ".local_module" in context.imports
        
        assert "DataProcessor" in context.class_definitions
        assert "process_file" in context.function_definitions
        assert "transform_data" in context.function_definitions
        assert "main" in context.function_definitions
        
        assert "API_KEY" in context.environment_vars
        assert "https://api.example.com/v1" in context.url_references
        assert "data.json" in context.file_references
        
        assert len(context.todos) == 1
        assert "Add validation logic" in context.todos[0]
        assert len(context.important_comments) == 1
        assert "FIXME" in context.important_comments[0]
    
    def test_javascript_preprocessing(self, preprocessor):
        """Test JavaScript file preprocessing"""
        content = '''
import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';
import './styles.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000';

export class UserService {
    async getUsers() {
        const response = await axios.get(`${API_URL}/api/users`);
        return response.data;
    }
}

export default function UserList() {
    const [users, setUsers] = useState([]);
    
    useEffect(() => {
        // TODO: Add error handling
        loadUsers();
    }, []);
    
    const loadUsers = async () => {
        const service = new UserService();
        const data = await service.getUsers();
        setUsers(data);
    };
    
    return (
        <div className="user-list">
            {users.map(user => (
                <div key={user.id}>{user.name}</div>
            ))}
        </div>
    );
}
'''
        
        context = preprocessor.preprocess_file(Path("UserList.jsx"), content)
        
        assert context.language == "javascript"
        assert "react" in context.imports
        assert "axios" in context.imports
        assert "./styles.css" in context.imports
        
        assert "UserService" in context.class_definitions
        assert "UserList" in context.function_definitions
        assert "getUsers" in context.function_definitions
        assert "loadUsers" in context.function_definitions
        
        assert "REACT_APP_API_URL" in context.environment_vars
        assert "http://localhost:3000" in context.url_references
        assert "/api/users" in context.url_references
        
        assert "UserService" in context.exports
        assert "UserList" in context.exports
    
    def test_config_file_preprocessing(self, preprocessor):
        """Test configuration file preprocessing"""
        content = '''{
    "name": "my-app",
    "version": "1.0.0",
    "scripts": {
        "start": "node server.js",
        "test": "jest",
        "build": "webpack --mode production"
    },
    "dependencies": {
        "express": "^4.17.1",
        "dotenv": "^10.0.0"
    },
    "config": {
        "port": "${PORT}",
        "database": "${DATABASE_URL}",
        "apiKey": "${API_KEY}"
    }
}'''
        
        context = preprocessor.preprocess_file(Path("package.json"), content)
        
        assert context.file_type == "build"
        assert "name" in context.config_values
        assert context.config_values["name"] == "my-app"
        
        assert "node server.js" in context.build_commands
        assert "jest" in context.build_commands
        assert "webpack --mode production" in context.build_commands
        
        assert "PORT" in context.environment_vars
        assert "DATABASE_URL" in context.environment_vars
        assert "API_KEY" in context.environment_vars
    
    def test_summary_generation(self, preprocessor):
        """Test summary generation for AI"""
        content = '''
import os
import requests
from database import User, Session

class UserManager:
    def __init__(self):
        self.db = Session()
        self.api_key = os.environ['API_KEY']
    
    def get_user(self, user_id):
        # TODO: Add caching
        return self.db.query(User).filter_by(id=user_id).first()
    
    def sync_with_api(self):
        response = requests.get(f"https://api.example.com/users")
        return response.json()
'''
        
        context = preprocessor.preprocess_file(Path("user_manager.py"), content)
        summary = context.to_summary()
        
        # Check that summary contains key information
        assert "File Type: source" in summary
        assert "Language: python" in summary
        assert "Imports (3): os, requests, database" in summary
        assert "Classes (1): UserManager" in summary
        assert "Functions (2): get_user, sync_with_api" in summary
        assert "Environment Variables: API_KEY" in summary
        assert "TODOs: 1" in summary
        assert "Add caching" in summary
    
    def test_test_file_preprocessing(self, preprocessor):
        """Test preprocessing of test files"""
        content = '''
import pytest
from unittest.mock import Mock, patch
from app.services import UserService

@pytest.fixture
def mock_database():
    """Mock database for testing"""
    db = Mock()
    db.query.return_value = []
    return db

@pytest.fixture
def user_service(mock_database):
    """Create user service with mocked dependencies"""
    return UserService(db=mock_database)

class TestUserService:
    def test_get_user(self, user_service):
        """Test getting a user"""
        user = user_service.get_user(123)
        assert user is not None
    
    @patch('app.services.requests')
    def test_api_call(self, mock_requests, user_service):
        """Test API integration"""
        mock_requests.get.return_value.json.return_value = {'users': []}
        result = user_service.sync_users()
        assert result == {'users': []}
'''
        
        context = preprocessor.preprocess_file(Path("test_user_service.py"), content)
        
        assert context.file_type == "test"
        assert "mock_database" in context.test_fixtures
        assert "user_service" in context.test_fixtures
        assert "TestUserService" in context.class_definitions
        assert "test_get_user" in context.function_definitions
        assert "test_api_call" in context.function_definitions
    
    def test_token_reduction(self, preprocessor):
        """Test that preprocessing significantly reduces content size"""
        # Create a large file with lots of boilerplate
        content = '''
"""
This is a very long module docstring that contains a lot of information
about the module, its purpose, usage examples, and other details that
while useful for documentation, are not critical for understanding
whether this file can be safely deleted.

Example usage:
    processor = DataProcessor()
    processor.process_all_files()
    
Author: John Doe
License: MIT
Version: 1.0.0
"""

import os
import sys
import json
import logging
import datetime
from typing import List, Dict, Optional, Union, Tuple
from collections import defaultdict
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 1024 * 1024 * 10  # 10MB
BATCH_SIZE = 100
TIMEOUT = 30
API_ENDPOINT = "https://api.example.com/v2/process"
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost/mydb')

class DataProcessor:
    """Main data processing class"""
    
    def __init__(self, config: Dict[str, any] = None):
        """Initialize the processor with configuration"""
        self.config = config or {}
        self.api_key = os.environ.get('API_KEY')
        self.batch_size = self.config.get('batch_size', BATCH_SIZE)
        self.processed_count = 0
        self.error_count = 0
        self.start_time = datetime.datetime.now()
        
        # Initialize connections
        self._init_database()
        self._init_api_client()
        
        logger.info(f"DataProcessor initialized with batch_size={self.batch_size}")
    
    def _init_database(self):
        """Initialize database connection"""
        # TODO: Implement proper connection pooling
        # FIXME: Add retry logic for connection failures
        pass
    
    def _init_api_client(self):
        """Initialize API client"""
        # WARNING: API key should be rotated regularly
        pass
    
    def process_file(self, file_path: Union[str, Path]) -> Dict[str, any]:
        """
        Process a single file and return results.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is too large
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.stat().st_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_path}")
        
        try:
            # Read and process file
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Validate data
            self._validate_data(data)
            
            # Transform data
            transformed = self._transform_data(data)
            
            # Send to API
            result = self._send_to_api(transformed)
            
            self.processed_count += 1
            return result
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error processing {file_path}: {e}")
            raise
    
    def _validate_data(self, data: Dict) -> None:
        """Validate input data"""
        required_fields = ['id', 'name', 'timestamp']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
    
    def _transform_data(self, data: Dict) -> Dict:
        """Transform data for API"""
        return {
            'id': data['id'],
            'name': data['name'].upper(),
            'timestamp': data['timestamp'],
            'processed_at': datetime.datetime.now().isoformat()
        }
    
    def _send_to_api(self, data: Dict) -> Dict:
        """Send data to external API"""
        # Implementation details...
        pass
    
    def process_batch(self, file_paths: List[Path]) -> List[Dict]:
        """Process multiple files in batch"""
        results = []
        for path in file_paths:
            try:
                result = self.process_file(path)
                results.append(result)
            except Exception as e:
                results.append({'error': str(e), 'file': str(path)})
        return results
    
    def get_stats(self) -> Dict[str, any]:
        """Get processing statistics"""
        elapsed = datetime.datetime.now() - self.start_time
        return {
            'processed': self.processed_count,
            'errors': self.error_count,
            'elapsed_seconds': elapsed.total_seconds(),
            'rate': self.processed_count / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0
        }

# Module-level functions
def create_processor(config_file: str = None) -> DataProcessor:
    """Factory function to create processor"""
    config = {}
    if config_file:
        with open(config_file, 'r') as f:
            config = json.load(f)
    return DataProcessor(config)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process data files')
    parser.add_argument('files', nargs='+', help='Files to process')
    parser.add_argument('--config', help='Configuration file')
    parser.add_argument('--batch', action='store_true', help='Process in batch mode')
    
    args = parser.parse_args()
    
    processor = create_processor(args.config)
    
    if args.batch:
        results = processor.process_batch([Path(f) for f in args.files])
    else:
        results = []
        for file_path in args.files:
            result = processor.process_file(file_path)
            results.append(result)
    
    print(json.dumps(results, indent=2))
    print(f"Stats: {processor.get_stats()}")

if __name__ == '__main__':
    main()
'''
        
        context = preprocessor.preprocess_file(Path("processor.py"), content)
        summary = context.to_summary()
        
        # Original content is very long
        assert len(content) > 5000
        
        # Summary should be much shorter
        assert len(summary) < 1000
        
        # But still contain key information
        assert "DataProcessor" in summary
        assert "process_file" in summary
        assert "API_KEY" in summary
        assert "DATABASE_URL" in summary
        assert "https://api.example.com/v2/process" in summary
        assert "TODO" in summary
        assert "FIXME" in summary
        assert "WARNING" in summary