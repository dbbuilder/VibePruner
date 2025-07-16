"""
Configuration module for VibePruner
"""

import json
import os
from pathlib import Path


class Config:
    """Configuration management for VibePruner"""
    
    def __init__(self, config_path=None):
        # Default configuration
        self.defaults = {
            'protected_patterns': [
                'README*', 'LICENSE*', 'CONTRIBUTING*', 'CHANGELOG*',
                'setup.py', 'requirements.txt', 'package.json', 'package-lock.json',
                '*.sln', '*.csproj', '*.config', 'appsettings*.json',
                '.gitignore', '.dockerignore', 'Dockerfile*',
                'Makefile', 'CMakeLists.txt', '*.yml', '*.yaml'
            ],
            'temp_patterns': [
                '*.tmp', '*.temp', '*.cache', '~*', '*.swp', '*.swo',
                '*.log', '*.bak', '*.backup', '*.old', '*.orig'
            ],
            'test_patterns': [
                '*test*', '*Test*', '*spec*', '*Spec*'
            ],
            'archive_path': '.vibepruner_archive',
            'max_file_size_mb': 100,
            'ignore_dirs': [
                '.git', '.vs', '.vscode', '.idea', '__pycache__',
                'node_modules', 'bin', 'obj', 'dist', 'build',
                '.pytest_cache', '.mypy_cache', 'venv', 'env'
            ],
            'confidence_thresholds': {
                'high': 0.7,
                'medium': 0.5,
                'low': 0.3
            }
        }
        
        # Load user configuration if provided
        self.config = self.defaults.copy()
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                self.config.update(user_config)
        
        # Create properties for easy access
        self._create_properties()
    
    def _create_properties(self):
        """Create properties from config dict"""
        for key, value in self.config.items():
            setattr(self, key, value)
    
    def save(self, path):
        """Save configuration to file"""
        with open(path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self.config[key] = value
        setattr(self, key, value)
