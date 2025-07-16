"""
AI-Enhanced File Analyzer - Integrates AI validation for safer file pruning
"""

import os
import re
import ast
import asyncio
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Optional, Set

from analyzer import FileAnalyzer
from ai_validation import ConsensusValidator, ConsensusMode
from ai_providers.base import FileValidationContext, ValidationStatus
from ai_providers.factory import create_default_providers

logger = logging.getLogger(__name__)


class AIFileAnalyzer(FileAnalyzer):
    """Enhanced file analyzer with AI-powered validation"""
    
    def __init__(self, config, ai_enabled: bool = True):
        super().__init__(config)
        self.ai_enabled = ai_enabled and config.get('ai_validation', {}).get('enabled', True)
        self.ai_validator = None
        self.ai_cache = {}  # Cache AI results by file content hash
        
        if self.ai_enabled:
            self._initialize_ai_validation()
    
    def _initialize_ai_validation(self):
        """Initialize AI validation components"""
        try:
            # Get AI configuration
            ai_config = self.config.get('ai_validation', {})
            
            # Create providers from configuration or environment
            providers = []
            if 'providers' in ai_config:
                # Create from explicit configuration
                from ai_providers.factory import ProviderFactory
                providers = ProviderFactory.create_providers_from_config(ai_config['providers'])
            else:
                # Create from environment variables
                providers = create_default_providers()
            
            if not providers:
                logger.warning("No AI providers available. AI validation disabled.")
                self.ai_enabled = False
                return
            
            # Create consensus validator
            consensus_mode = ConsensusMode(ai_config.get('consensus_mode', 'majority'))
            confidence_threshold = ai_config.get('confidence_threshold', 0.8)
            
            self.ai_validator = ConsensusValidator(
                providers=providers,
                consensus_mode=consensus_mode,
                confidence_threshold=confidence_threshold
            )
            
            logger.info(f"AI validation initialized with {len(providers)} providers")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI validation: {e}")
            self.ai_enabled = False
    
    async def analyze_directory_with_ai(self, project_path):
        """Analyze directory with AI-enhanced validation"""
        # First do standard analysis
        analysis = self.analyze_directory(project_path)
        
        if not self.ai_enabled or not self.ai_validator:
            return analysis
        
        # Add AI validation results
        analysis['ai_validation'] = {}
        
        # Get batch size from config
        batch_size = self.config.get('ai_validation', {}).get('batch_size', 10)
        
        # Process files in batches for efficiency
        file_items = list(analysis['files'].items())
        total_files = len(file_items)
        
        print(f"\n[AI] Validating {total_files} files with AI providers...")
        
        for i in range(0, total_files, batch_size):
            batch = file_items[i:i + batch_size]
            batch_results = await self._validate_batch(batch, project_path)
            analysis['ai_validation'].update(batch_results)
            
            # Progress update
            processed = min(i + batch_size, total_files)
            print(f"[AI] Processed {processed}/{total_files} files...")
        
        # Update orphaned files list based on AI recommendations
        analysis['ai_unsafe_files'] = self._identify_ai_unsafe_files(analysis)
        
        print(f"[AI] Validation complete. {len(analysis['ai_unsafe_files'])} files marked as unsafe by AI.")
        
        return analysis
    
    async def _validate_batch(self, batch: List[tuple], project_path: Path) -> Dict:
        """Validate a batch of files with AI"""
        results = {}
        tasks = []
        
        for file_path, file_info in batch:
            # Skip if already cached
            content_hash = self._get_file_content_hash(project_path / file_path)
            if content_hash in self.ai_cache:
                results[file_path] = self.ai_cache[content_hash]
                continue
            
            # Create validation context
            context = self._create_validation_context(file_path, file_info, project_path)
            if context:
                tasks.append(self._validate_file_with_cache(file_path, context, content_hash))
        
        # Run validations concurrently
        if tasks:
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for file_path, result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"AI validation error for {file_path}: {result}")
                    results[file_path] = None
                else:
                    results[file_path] = result
        
        return results
    
    async def _validate_file_with_cache(self, file_path: str, context: FileValidationContext, content_hash: str):
        """Validate file and cache result"""
        try:
            result = await self.ai_validator.validate_file(context)
            self.ai_cache[content_hash] = result
            return (file_path, result)
        except Exception as e:
            logger.error(f"Error validating {file_path}: {e}")
            return (file_path, e)
    
    def _create_validation_context(self, file_path: str, file_info: dict, project_path: Path) -> Optional[FileValidationContext]:
        """Create validation context for a file"""
        try:
            full_path = project_path / file_path
            
            # Read file content
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Skip very large files
            if len(content) > 100000:  # 100KB limit
                return None
            
            # Determine file type category
            file_type = self._categorize_file_type(file_path, file_info)
            
            # Get dependencies and dependents from analysis
            dependencies = file_info.get('imports', [])
            dependents = self._find_dependents(file_path, project_path)
            
            return FileValidationContext(
                file_path=str(full_path),
                file_content=content,
                file_type=file_type,
                file_size=file_info['size'],
                dependencies=dependencies,
                dependents=dependents,
                project_context={
                    'is_test': file_info.get('is_test', False),
                    'is_temp': file_info.get('is_temp', False),
                    'days_since_modified': file_info.get('days_since_modified', 0),
                    'reference_count': file_info.get('reference_count', 0)
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating validation context for {file_path}: {e}")
            return None
    
    def _categorize_file_type(self, file_path: str, file_info: dict) -> str:
        """Categorize file type for AI context"""
        path_lower = file_path.lower()
        ext = file_info.get('extension', '').lower()
        
        # Test files
        if file_info.get('is_test'):
            return 'test'
        
        # Configuration files
        config_patterns = ['config', 'settings', '.env', '.ini', '.yaml', '.yml', '.toml']
        if any(pattern in path_lower for pattern in config_patterns):
            return 'config'
        
        # Build files
        build_files = ['makefile', 'cmake', '.gradle', 'pom.xml', 'package.json', '.csproj', '.sln']
        if any(pattern in path_lower for pattern in build_files):
            return 'build'
        
        # CI/CD files
        if '.github' in path_lower or '.gitlab' in path_lower or 'jenkins' in path_lower:
            return 'ci'
        
        # Migration files
        if 'migration' in path_lower or 'migrate' in path_lower:
            return 'migration'
        
        # Interface/contract files
        if 'interface' in path_lower or 'abstract' in path_lower or ext in ['.proto', '.thrift']:
            return 'interface'
        
        # Schema files
        if 'schema' in path_lower or ext in ['.graphql', '.gql']:
            return 'schema'
        
        # Fixture/mock files
        if 'fixture' in path_lower or 'mock' in path_lower:
            return 'fixture'
        
        # Default to file extension
        return ext.lstrip('.') if ext else 'unknown'
    
    def _find_dependents(self, target_file: str, project_path: Path) -> List[str]:
        """Find files that depend on the target file"""
        dependents = []
        
        # This would be populated from the dependency graph
        # For now, return empty list - could be enhanced with actual dependency tracking
        return dependents
    
    def _get_file_content_hash(self, file_path: Path) -> str:
        """Get hash of file content for caching"""
        import hashlib
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return str(file_path)  # Fallback to path if can't read
    
    def _identify_ai_unsafe_files(self, analysis: dict) -> List[str]:
        """Identify files marked as unsafe by AI"""
        unsafe_files = []
        
        for file_path, ai_result in analysis.get('ai_validation', {}).items():
            if ai_result and hasattr(ai_result, 'consensus_status'):
                if ai_result.consensus_status == ValidationStatus.UNSAFE:
                    unsafe_files.append(file_path)
                elif ai_result.consensus_status == ValidationStatus.UNCERTAIN:
                    # Also mark uncertain files as potentially unsafe
                    if ai_result.average_confidence < 0.5:
                        unsafe_files.append(file_path)
        
        return unsafe_files
    
    def get_ai_confidence_adjustment(self, file_path: str, ai_validation_results: dict) -> float:
        """Get confidence score adjustment based on AI validation"""
        if not self.ai_enabled or file_path not in ai_validation_results:
            return 0.0
        
        ai_result = ai_validation_results[file_path]
        if not ai_result:
            return 0.0
        
        # Adjust confidence based on AI consensus
        if ai_result.consensus_status == ValidationStatus.SAFE:
            # AI agrees it's safe - boost confidence
            return 0.3 * ai_result.average_confidence
        elif ai_result.consensus_status == ValidationStatus.UNSAFE:
            # AI thinks it's unsafe - reduce confidence significantly
            return -0.5 * ai_result.average_confidence
        else:  # UNCERTAIN
            # AI is uncertain - slight reduction
            return -0.2 * (1.0 - ai_result.average_confidence)