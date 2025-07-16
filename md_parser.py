"""
Markdown Parser - Analyzes markdown files for file references and importance indicators
"""

import re
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MarkdownParser:
    """Parses markdown files to find file references and importance indicators"""
    
    def __init__(self, config):
        self.config = config
        
        # Importance keywords
        self.required_keywords = [
            'required', 'essential', 'critical', 'must have', 'necessary',
            'mandatory', 'depends on', 'prerequisite'
        ]
        
        self.temporary_keywords = [
            'temporary', 'temp', 'tmp', 'deprecated', 'obsolete', 'old',
            'remove', 'delete', 'cleanup', 'todo: remove', 'fixme: remove'
        ]
        
        # File reference patterns
        self.file_patterns = [
            # Links: [text](file.ext)
            r'\[([^\]]+)\]\(([^)]+)\)',
            # Code blocks: `file.ext`
            r'`([^`]+\.[a-zA-Z0-9]+)`',
            # File paths: path/to/file.ext
            r'(?:^|\s)([\.\/\w\-\\]+\.[a-zA-Z0-9]+)(?:\s|$)',
            # Import/include statements in code blocks
            r'(?:import|include|require|from)\s+["\']?([^"\'\s]+)["\']?',
            # Command line examples
            r'(?:python|node|dotnet|npm|yarn)\s+([^\s]+\.[a-zA-Z0-9]+)'
        ]
    
    def analyze_markdown_files(self, project_path):
        """Analyze all markdown files in the project"""
        project_path = Path(project_path)
        analysis = {
            'markdown_files': [],
            'referenced_files': set(),
            'required_files': set(),
            'temporary_files': set(),
            'file_mentions': {},  # file -> list of (md_file, context)
            'importance_scores': {}  # file -> score
        }
        
        # Find all markdown files
        md_files = list(project_path.rglob('*.md')) + list(project_path.rglob('*.MD'))
        
        for md_file in md_files:
            try:
                relative_path = md_file.relative_to(project_path)
                logger.info(f"Analyzing markdown: {relative_path}")
                
                with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Analyze this markdown file
                file_analysis = self._analyze_single_markdown(content, md_file, project_path)
                
                # Update aggregate analysis
                analysis['markdown_files'].append(str(relative_path))
                analysis['referenced_files'].update(file_analysis['referenced_files'])
                analysis['required_files'].update(file_analysis['required_files'])
                analysis['temporary_files'].update(file_analysis['temporary_files'])
                
                # Track mentions
                for file in file_analysis['referenced_files']:
                    if file not in analysis['file_mentions']:
                        analysis['file_mentions'][file] = []
                    analysis['file_mentions'][file].append({
                        'md_file': str(relative_path),
                        'importance': self._get_md_importance(str(relative_path))
                    })
                
                # Update importance scores
                for file, score in file_analysis['importance_scores'].items():
                    if file not in analysis['importance_scores']:
                        analysis['importance_scores'][file] = 0
                    analysis['importance_scores'][file] += score
                    
            except Exception as e:
                logger.error(f"Error analyzing {md_file}: {e}")
        
        # Convert sets to lists for JSON serialization
        analysis['referenced_files'] = list(analysis['referenced_files'])
        analysis['required_files'] = list(analysis['required_files'])
        analysis['temporary_files'] = list(analysis['temporary_files'])
        
        return analysis
    
    def _analyze_single_markdown(self, content, md_file, project_path):
        """Analyze a single markdown file"""
        analysis = {
            'referenced_files': set(),
            'required_files': set(),
            'temporary_files': set(),
            'importance_scores': {}
        }
        
        # Extract all file references
        for pattern in self.file_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                # Handle different match types
                if isinstance(match, tuple):
                    # Link pattern returns (text, url)
                    file_ref = match[1] if len(match) > 1 else match[0]
                else:
                    file_ref = match
                
                # Clean up the reference
                file_ref = file_ref.strip()
                
                # Skip URLs and anchors
                if file_ref.startswith(('http://', 'https://', '#', 'mailto:')):
                    continue
                
                # Skip if no file extension
                if '.' not in file_ref:
                    continue
                
                # Try to resolve the file path
                resolved_path = self._resolve_file_path(file_ref, md_file, project_path)
                if resolved_path:
                    analysis['referenced_files'].add(resolved_path)
                    
                    # Check context for importance
                    context = self._get_file_context(content, file_ref)
                    importance = self._analyze_context_importance(context)
                    
                    if importance == 'required':
                        analysis['required_files'].add(resolved_path)
                    elif importance == 'temporary':
                        analysis['temporary_files'].add(resolved_path)
                    
                    # Calculate importance score
                    md_importance = self._get_md_importance(md_file.name)
                    analysis['importance_scores'][resolved_path] = md_importance
        
        return analysis
    
    def _resolve_file_path(self, file_ref, md_file, project_path):
        """Resolve a file reference to an actual path"""
        # Remove any markdown link syntax
        file_ref = re.sub(r'^\[.*\]\((.+)\)$', r'\1', file_ref)
        
        # Try different path resolutions
        candidates = []
        
        # 1. Relative to markdown file
        md_dir = md_file.parent
        candidates.append(md_dir / file_ref)
        
        # 2. Relative to project root
        candidates.append(project_path / file_ref)
        
        # 3. If it starts with ./, relative to md file
        if file_ref.startswith('./'):
            candidates.append(md_dir / file_ref[2:])
        
        # 4. Search for the filename in project
        filename = Path(file_ref).name
        if filename:
            for found in project_path.rglob(filename):
                candidates.append(found)
        
        # Return first existing candidate
        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return str(candidate.relative_to(project_path))
            except:
                pass
        
        return None
    
    def _get_file_context(self, content, file_ref, context_lines=3):
        """Get the context around a file reference"""
        lines = content.split('\n')
        context = []
        
        for i, line in enumerate(lines):
            if file_ref in line:
                # Get surrounding lines
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context.extend(lines[start:end])
        
        return '\n'.join(context)
    
    def _analyze_context_importance(self, context):
        """Analyze the context to determine file importance"""
        context_lower = context.lower()
        
        # Check for required keywords
        for keyword in self.required_keywords:
            if keyword in context_lower:
                return 'required'
        
        # Check for temporary keywords
        for keyword in self.temporary_keywords:
            if keyword in context_lower:
                return 'temporary'
        
        return 'normal'
    
    def _get_md_importance(self, md_filename):
        """Get importance score based on markdown filename"""
        filename_lower = md_filename.lower()
        
        # High importance files
        if filename_lower in ['readme.md', 'setup.md', 'install.md', 'installation.md']:
            return 1.0
        elif filename_lower in ['architecture.md', 'design.md', 'api.md', 'reference.md']:
            return 0.8
        elif filename_lower in ['contributing.md', 'development.md', 'building.md']:
            return 0.7
        elif filename_lower in ['changelog.md', 'history.md', 'releases.md']:
            return 0.5
        elif filename_lower in ['todo.md', 'notes.md', 'draft.md']:
            return 0.3
        else:
            return 0.4
