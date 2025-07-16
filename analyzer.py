"""
File Analyzer - Analyzes files and builds dependency graph
"""

import os
import re
import ast
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FileAnalyzer:
    """Analyzes files to build dependency graph"""
    
    def __init__(self, config):
        self.config = config
        self.import_patterns = {
            'python': [
                r'^\s*import\s+(\S+)',
                r'^\s*from\s+(\S+)\s+import',
            ],
            'javascript': [
                r'^\s*import\s+.*\s+from\s+[\'"]([^\'\"]+)[\'"]',
                r'^\s*const\s+\w+\s*=\s*require\([\'"]([^\'\"]+)[\'"]\)',
                r'^\s*require\([\'"]([^\'\"]+)[\'"]\)',
            ],
            'typescript': [
                r'^\s*import\s+.*\s+from\s+[\'"]([^\'\"]+)[\'"]',
                r'^\s*import\s+[\'"]([^\'\"]+)[\'"]',
            ],
            'csharp': [
                r'^\s*using\s+(\S+);',
                r'^\s*using\s+static\s+(\S+);',
            ],
            'java': [
                r'^\s*import\s+(\S+);',
                r'^\s*import\s+static\s+(\S+);',
            ],
            'cpp': [
                r'^\s*#include\s*[<"]([^>"]+)[>"]',
            ],
            'go': [
                r'^\s*import\s+"([^"]+)"',
                r'^\s*import\s+\(\s*"([^"]+)"',
            ],
            'rust': [
                r'^\s*use\s+(\S+)',
                r'^\s*extern\s+crate\s+(\S+)',
            ],
            'sql': [
                r'^\s*(?:EXEC|EXECUTE)\s+(\S+)',
                r'^\s*(?:FROM|JOIN)\s+(\S+)',
            ],
        }
        
        self.skip_dirs = {
            '.git', '.vs', '.vscode', '.idea', '__pycache__', 
            'node_modules', 'bin', 'obj', 'dist', 'build',
            '.pytest_cache', '.mypy_cache', 'venv', 'env'
        }
    
    def analyze_directory(self, project_path):
        """Analyze all files in directory"""
        project_path = Path(project_path)
        analysis = {
            'total_files': 0,
            'files': {},
            'dependencies': {},
            'orphaned_files': [],
            'file_types': {}
        }
        
        # Scan all files
        for file_path in self._scan_files(project_path):
            relative_path = file_path.relative_to(project_path)
            
            # Skip files in skip directories
            if any(skip_dir in relative_path.parts for skip_dir in self.skip_dirs):
                continue
            
            file_info = self._analyze_file(file_path, project_path)
            analysis['files'][str(relative_path)] = file_info
            analysis['total_files'] += 1
            
            # Track file types
            ext = file_path.suffix.lower()
            if ext not in analysis['file_types']:
                analysis['file_types'][ext] = 0
            analysis['file_types'][ext] += 1
        
        # Build dependency graph
        analysis['dependencies'] = self._build_dependency_graph(analysis['files'], project_path)
        
        # Find orphaned files
        analysis['orphaned_files'] = self._find_orphaned_files(analysis['files'], analysis['dependencies'])
        
        return analysis
    
    def _scan_files(self, directory):
        """Recursively scan for files"""
        for root, dirs, files in os.walk(directory):
            # Remove skip directories
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]
            
            for file in files:
                yield Path(root) / file
    
    def _analyze_file(self, file_path, project_path):
        """Analyze a single file"""
        stat = file_path.stat()
        
        file_info = {
            'path': str(file_path),
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'days_since_modified': (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days,
            'extension': file_path.suffix.lower(),
            'imports': [],
            'reference_count': 0,
            'is_test': self._is_test_file(file_path),
            'is_temp': self._is_temp_file(file_path)
        }
        
        # Extract imports/dependencies based on file type
        file_type = self._get_file_type(file_path)
        if file_type and file_type in self.import_patterns:
            file_info['imports'] = self._extract_imports(file_path, file_type)
        
        return file_info
    
    def _get_file_type(self, file_path):
        """Determine file type from extension"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.cs': 'csharp',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.h': 'cpp',
            '.hpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.sql': 'sql'
        }
        
        return ext_map.get(file_path.suffix.lower())
    
    def _extract_imports(self, file_path, file_type):
        """Extract import statements from file"""
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            patterns = self.import_patterns.get(file_type, [])
            for pattern in patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                imports.extend(matches)
            
            # Clean up imports
            imports = [self._clean_import(imp, file_type) for imp in imports]
            imports = [imp for imp in imports if imp]  # Remove empty
            
        except Exception as e:
            logger.error(f"Error extracting imports from {file_path}: {e}")
        
        return list(set(imports))  # Remove duplicates
    
    def _clean_import(self, import_str, file_type):
        """Clean up import string"""
        # Remove quotes, semicolons, etc.
        import_str = import_str.strip('"\'`;')
        
        # Handle relative imports
        if import_str.startswith('.'):
            return import_str  # Keep relative imports as-is
        
        # Language-specific cleaning
        if file_type == 'python':
            # Remove submodules for main module reference
            parts = import_str.split('.')
            if len(parts) > 1 and parts[0] not in ['os', 'sys']:
                return parts[0]
        elif file_type in ['javascript', 'typescript']:
            # Remove file extensions
            import_str = re.sub(r'\.(js|ts|jsx|tsx)$', '', import_str)
        
        return import_str
    
    def _is_test_file(self, file_path):
        """Check if file is a test file"""
        name_lower = file_path.name.lower()
        patterns = [
            'test_', '_test.', 'test.', '.test.',
            'spec_', '_spec.', 'spec.', '.spec.',
            'tests.', 'testing.'
        ]
        
        return any(pattern in name_lower for pattern in patterns)
    
    def _is_temp_file(self, file_path):
        """Check if file is temporary"""
        name_lower = file_path.name.lower()
        patterns = [
            'tmp', 'temp', 'backup', 'bak', 'old', 'copy',
            '~', '.swp', '.swo', '.log', '.cache'
        ]
        
        return any(pattern in name_lower for pattern in patterns)
    
    def _build_dependency_graph(self, files, project_path):
        """Build dependency graph from imports"""
        dependencies = {}
        
        for file_path, file_info in files.items():
            dependencies[file_path] = []
            
            for import_ref in file_info['imports']:
                # Try to resolve import to actual file
                resolved = self._resolve_import(import_ref, file_path, files, project_path)
                if resolved and resolved != file_path:
                    dependencies[file_path].append(resolved)
                    # Increment reference count
                    if resolved in files:
                        files[resolved]['reference_count'] += 1
        
        return dependencies
    
    def _resolve_import(self, import_ref, importing_file, all_files, project_path):
        """Resolve an import reference to an actual file"""
        importing_path = Path(importing_file)
        
        # Handle relative imports
        if import_ref.startswith('.'):
            base_dir = importing_path.parent
            levels = len(re.match(r'^\.+', import_ref).group())
            
            # Go up directories
            for _ in range(levels - 1):
                base_dir = base_dir.parent
            
            # Remove dots and get module name
            module = import_ref.lstrip('.')
            if module:
                return self._find_module_file(module, str(base_dir), all_files)
        else:
            # Absolute import - search from project root
            return self._find_module_file(import_ref, '', all_files)
        
        return None
    
    def _find_module_file(self, module_name, base_path, all_files):
        """Find actual file for a module name"""
        # Common file extensions to try
        extensions = ['.py', '.js', '.ts', '.cs', '.java', '.go', '.rs']
        
        # Possible file names
        candidates = []
        
        # Direct file match
        if base_path:
            candidates.append(f"{base_path}/{module_name}")
            candidates.append(f"{base_path}/{module_name}/index")
            candidates.append(f"{base_path}/{module_name}/__init__.py")
        else:
            candidates.append(module_name)
            candidates.append(f"{module_name}/index")
            candidates.append(f"{module_name}/__init__.py")
        
        # Try each candidate with extensions
        for candidate in candidates:
            # Clean up path
            candidate = candidate.replace('\\', '/').lstrip('/')
            
            # Check exact match first
            if candidate in all_files:
                return candidate
            
            # Try with extensions
            for ext in extensions:
                full_candidate = f"{candidate}{ext}"
                if full_candidate in all_files:
                    return full_candidate
        
        # Try partial match (module might be in subdirectory)
        module_parts = module_name.split('/')
        if module_parts:
            last_part = module_parts[-1]
            for file_path in all_files:
                if file_path.endswith(f"/{last_part}.py") or \
                   file_path.endswith(f"/{last_part}.js") or \
                   file_path.endswith(f"/{last_part}.ts"):
                    return file_path
        
        return None
    
    def _find_orphaned_files(self, files, dependencies):
        """Find files with no incoming references"""
        orphaned = []
        
        # Build set of all referenced files
        referenced = set()
        for deps in dependencies.values():
            referenced.update(deps)
        
        # Find files not referenced
        for file_path, file_info in files.items():
            if file_path not in referenced and file_info['reference_count'] == 0:
                # Skip certain files that are typically entry points
                if self._is_entry_point(file_path):
                    continue
                
                # Skip test files (they're usually not imported)
                if file_info['is_test']:
                    continue
                
                orphaned.append(file_path)
        
        return orphaned
    
    def _is_entry_point(self, file_path):
        """Check if file is likely an entry point"""
        entry_patterns = [
            'main.py', '__main__.py', 'app.py', 'run.py',
            'index.js', 'app.js', 'server.js',
            'Program.cs', 'Startup.cs',
            'Main.java', 'Application.java',
            'main.go', 'main.rs'
        ]
        
        return any(file_path.endswith(pattern) for pattern in entry_patterns)
