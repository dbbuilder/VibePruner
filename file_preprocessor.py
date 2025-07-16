"""
File Pre-processor for AI Validation - Reduces token usage by extracting key information
"""

import re
import ast
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FileContext:
    """Extracted context from a file for AI validation"""
    # Core identifiers
    file_type: str
    language: str
    
    # Extracted elements
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    class_definitions: List[str] = field(default_factory=list)
    function_definitions: List[str] = field(default_factory=list)
    
    # Dependencies and references
    external_calls: List[str] = field(default_factory=list)
    file_references: List[str] = field(default_factory=list)
    url_references: List[str] = field(default_factory=list)
    database_references: List[str] = field(default_factory=list)
    
    # Configuration and constants
    constants: Dict[str, Any] = field(default_factory=dict)
    config_values: Dict[str, Any] = field(default_factory=dict)
    environment_vars: List[str] = field(default_factory=list)
    
    # Build and deployment
    build_commands: List[str] = field(default_factory=list)
    script_references: List[str] = field(default_factory=list)
    
    # Documentation and metadata
    docstrings: List[str] = field(default_factory=list)
    todos: List[str] = field(default_factory=list)
    important_comments: List[str] = field(default_factory=list)
    
    # Test-related
    test_fixtures: List[str] = field(default_factory=list)
    test_dependencies: List[str] = field(default_factory=list)
    
    # Metrics
    line_count: int = 0
    complexity_indicators: int = 0  # Loops, conditions, etc.
    
    def to_summary(self) -> str:
        """Convert to a concise summary for AI analysis"""
        parts = [
            f"File Type: {self.file_type}",
            f"Language: {self.language}",
            f"Lines: {self.line_count}",
        ]
        
        if self.imports:
            parts.append(f"\nImports ({len(self.imports)}): {', '.join(self.imports[:10])}")
            if len(self.imports) > 10:
                parts.append(f"  ... and {len(self.imports) - 10} more")
        
        if self.exports:
            parts.append(f"\nExports ({len(self.exports)}): {', '.join(self.exports[:5])}")
        
        if self.class_definitions:
            parts.append(f"\nClasses ({len(self.class_definitions)}): {', '.join(self.class_definitions[:5])}")
        
        if self.function_definitions:
            parts.append(f"\nFunctions ({len(self.function_definitions)}): {', '.join(self.function_definitions[:10])}")
        
        if self.external_calls:
            parts.append(f"\nExternal Calls: {', '.join(set(self.external_calls)[:10])}")
        
        if self.file_references:
            parts.append(f"\nFile References: {', '.join(self.file_references[:5])}")
        
        if self.database_references:
            parts.append(f"\nDatabase References: {', '.join(self.database_references[:5])}")
        
        if self.environment_vars:
            parts.append(f"\nEnvironment Variables: {', '.join(self.environment_vars[:5])}")
        
        if self.build_commands:
            parts.append(f"\nBuild Commands: {', '.join(self.build_commands[:3])}")
        
        if self.test_fixtures:
            parts.append(f"\nTest Fixtures: {', '.join(self.test_fixtures[:5])}")
        
        if self.important_comments:
            parts.append(f"\nImportant Comments: {len(self.important_comments)}")
            for comment in self.important_comments[:3]:
                parts.append(f"  - {comment[:100]}")
        
        if self.todos:
            parts.append(f"\nTODOs: {len(self.todos)}")
            for todo in self.todos[:2]:
                parts.append(f"  - {todo[:80]}")
        
        return "\n".join(parts)


class FilePreprocessor:
    """Pre-processes files to extract key information for AI analysis"""
    
    def __init__(self):
        # Patterns for various extractions
        self.import_patterns = {
            'python': [
                re.compile(r'^\s*import\s+(\S+)', re.MULTILINE),
                re.compile(r'^\s*from\s+(\S+)\s+import', re.MULTILINE),
            ],
            'javascript': [
                re.compile(r'^\s*import\s+.*?\s+from\s+[\'"]([^\'\"]+)[\'"]', re.MULTILINE),
                re.compile(r'^\s*const\s+.*?\s*=\s*require\([\'"]([^\'\"]+)[\'"]\)', re.MULTILINE),
                re.compile(r'^\s*require\([\'"]([^\'\"]+)[\'"]\)', re.MULTILINE),
            ],
            'typescript': [
                re.compile(r'^\s*import\s+.*?\s+from\s+[\'"]([^\'\"]+)[\'"]', re.MULTILINE),
                re.compile(r'^\s*import\s+[\'"]([^\'\"]+)[\'"]', re.MULTILINE),
                re.compile(r'^\s*export\s+.*?\s+from\s+[\'"]([^\'\"]+)[\'"]', re.MULTILINE),
            ],
            'csharp': [
                re.compile(r'^\s*using\s+(\S+);', re.MULTILINE),
                re.compile(r'^\s*using\s+static\s+(\S+);', re.MULTILINE),
            ],
            'java': [
                re.compile(r'^\s*import\s+(\S+);', re.MULTILINE),
                re.compile(r'^\s*import\s+static\s+(\S+);', re.MULTILINE),
            ],
            'go': [
                re.compile(r'^\s*import\s+"([^"]+)"', re.MULTILINE),
                re.compile(r'^\s*import\s+\(\s*"([^"]+)"', re.MULTILINE),
            ],
        }
        
        # File reference patterns
        self.file_ref_patterns = [
            re.compile(r'[\'"]([^\'\"]*\.(py|js|ts|cs|java|go|rs|cpp|c|h|hpp))[\'"]'),
            re.compile(r'[\'"](\./[^\'\"]+)[\'"]'),
            re.compile(r'[\'"](\.\./[^\'\"]+)[\'"]'),
            re.compile(r'open\([\'"]([^\'\"]+)[\'"]'),
            re.compile(r'File\([\'"]([^\'\"]+)[\'"]'),
            re.compile(r'path\.join\([^)]*[\'"]([^\'\"]+)[\'"]'),
        ]
        
        # URL patterns
        self.url_patterns = [
            re.compile(r'https?://[^\s\'"<>]+'),
            re.compile(r'[\'"](/api/[^\'\"]+)[\'"]'),
            re.compile(r'[\'"](/v\d+/[^\'\"]+)[\'"]'),
        ]
        
        # Database patterns
        self.db_patterns = [
            re.compile(r'(?:SELECT|INSERT|UPDATE|DELETE|FROM|JOIN)\s+(\w+)', re.IGNORECASE),
            re.compile(r'(?:table|Table)\([\'"](\w+)[\'"]'),
            re.compile(r'(?:collection|Collection)\([\'"](\w+)[\'"]'),
            re.compile(r'db\.(\w+)\.'),
        ]
        
        # Environment variable patterns
        self.env_patterns = [
            re.compile(r'(?:process\.env|os\.environ|ENV|Environment)\[?\.?[\'"]?(\w+)'),
            re.compile(r'\$\{(\w+)\}'),
            re.compile(r'getenv\([\'"](\w+)[\'"]'),
        ]
        
        # Build command patterns
        self.build_patterns = [
            re.compile(r'(?:npm|yarn|pnpm)\s+(run|test|build|start)\s+(\S+)'),
            re.compile(r'(?:make|cmake|gradle|maven|cargo|go)\s+(\S+)'),
            re.compile(r'(?:dotnet|msbuild)\s+(\S+)'),
            re.compile(r'(?:python|pip)\s+(\S+)'),
        ]
        
        # Important comment patterns
        self.important_comment_patterns = [
            re.compile(r'#\s*(TODO|FIXME|HACK|BUG|XXX|IMPORTANT|WARNING|DEPRECATED):?\s*(.+)', re.IGNORECASE),
            re.compile(r'//\s*(TODO|FIXME|HACK|BUG|XXX|IMPORTANT|WARNING|DEPRECATED):?\s*(.+)', re.IGNORECASE),
            re.compile(r'/\*\s*(TODO|FIXME|HACK|BUG|XXX|IMPORTANT|WARNING|DEPRECATED):?\s*(.+?)\*/', re.IGNORECASE | re.DOTALL),
        ]
        
        # Test patterns
        self.test_patterns = [
            re.compile(r'(?:describe|it|test|expect)\([\'"]([^\'\"]+)[\'"]'),
            re.compile(r'@pytest\.fixture'),
            re.compile(r'class\s+(\w*Test\w*)\s*[:\(]'),
            re.compile(r'def\s+(test_\w+)\s*\('),
        ]
    
    def preprocess_file(self, file_path: Path, content: str) -> FileContext:
        """Extract key information from a file"""
        context = FileContext(
            file_type=self._determine_file_type(file_path),
            language=self._determine_language(file_path),
            line_count=len(content.splitlines())
        )
        
        # Extract based on language
        if context.language in ['python', 'javascript', 'typescript', 'csharp', 'java', 'go']:
            self._extract_code_elements(content, context)
        elif context.file_type == 'config':
            self._extract_config_elements(content, context)
        elif context.file_type == 'build':
            self._extract_build_elements(content, context)
        elif context.file_type == 'documentation':
            self._extract_doc_elements(content, context)
        
        # Common extractions for all files
        self._extract_file_references(content, context)
        self._extract_urls(content, context)
        self._extract_environment_vars(content, context)
        self._extract_important_comments(content, context)
        
        # Test-specific extractions
        if 'test' in str(file_path).lower():
            self._extract_test_elements(content, context)
        
        return context
    
    def _determine_file_type(self, file_path: Path) -> str:
        """Determine the type of file"""
        name_lower = file_path.name.lower()
        ext = file_path.suffix.lower()
        
        # Config files
        if any(pattern in name_lower for pattern in ['config', 'settings', '.env', 'appsettings']):
            return 'config'
        if ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.xml']:
            return 'config'
        
        # Build files
        if name_lower in ['makefile', 'dockerfile', 'cmakelists.txt', 'package.json', 'pom.xml', 'build.gradle']:
            return 'build'
        if ext in ['.mk', '.cmake']:
            return 'build'
        
        # Test files
        if any(pattern in name_lower for pattern in ['test', 'spec', 'fixture']):
            return 'test'
        
        # Documentation
        if ext in ['.md', '.rst', '.txt', '.adoc']:
            return 'documentation'
        
        # Source code
        if ext in ['.py', '.js', '.ts', '.cs', '.java', '.go', '.rs', '.cpp', '.c', '.h']:
            return 'source'
        
        # SQL
        if ext in ['.sql', '.ddl', '.dml']:
            return 'database'
        
        return 'unknown'
    
    def _determine_language(self, file_path: Path) -> str:
        """Determine programming language"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.cs': 'csharp',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.sql': 'sql',
            '.sh': 'shell',
            '.ps1': 'powershell',
            '.rb': 'ruby',
            '.php': 'php',
        }
        
        return ext_map.get(file_path.suffix.lower(), 'unknown')
    
    def _extract_code_elements(self, content: str, context: FileContext):
        """Extract code-specific elements"""
        language = context.language
        
        # Extract imports
        if language in self.import_patterns:
            for pattern in self.import_patterns[language]:
                matches = pattern.findall(content)
                context.imports.extend(matches)
        
        # Language-specific extractions
        if language == 'python':
            self._extract_python_elements(content, context)
        elif language in ['javascript', 'typescript']:
            self._extract_javascript_elements(content, context)
        elif language == 'csharp':
            self._extract_csharp_elements(content, context)
        elif language == 'java':
            self._extract_java_elements(content, context)
        elif language == 'go':
            self._extract_go_elements(content, context)
    
    def _extract_python_elements(self, content: str, context: FileContext):
        """Extract Python-specific elements"""
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Classes
                if isinstance(node, ast.ClassDef):
                    context.class_definitions.append(node.name)
                    # Check for test fixtures
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and 'fixture' in decorator.id:
                            context.test_fixtures.append(node.name)
                
                # Functions
                elif isinstance(node, ast.FunctionDef):
                    context.function_definitions.append(node.name)
                    # Check for exports
                    if node.name.startswith('__') and not node.name.endswith('__'):
                        continue
                    if not node.name.startswith('_'):
                        context.exports.append(node.name)
                
                # External calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        context.external_calls.append(node.func.attr)
                    elif isinstance(node.func, ast.Name):
                        context.external_calls.append(node.func.id)
                
                # Constants
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            try:
                                value = ast.literal_eval(node.value)
                                context.constants[target.id] = value
                            except:
                                pass
        
        except SyntaxError:
            # Fallback to regex for invalid Python
            self._extract_with_regex(content, context)
    
    def _extract_javascript_elements(self, content: str, context: FileContext):
        """Extract JavaScript/TypeScript elements"""
        # Classes
        class_pattern = re.compile(r'(?:export\s+)?(?:default\s+)?class\s+(\w+)')
        context.class_definitions.extend(class_pattern.findall(content))
        
        # Functions
        func_patterns = [
            re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)'),
            re.compile(r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\('),
            re.compile(r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?function'),
        ]
        for pattern in func_patterns:
            context.function_definitions.extend(pattern.findall(content))
        
        # Exports
        export_pattern = re.compile(r'export\s+(?:default\s+)?(?:{[^}]+}|(\w+))')
        context.exports.extend([m for m in export_pattern.findall(content) if m])
        
        # External calls (common patterns)
        call_patterns = [
            re.compile(r'(\w+)\.(\w+)\('),  # object.method()
            re.compile(r'await\s+(\w+)\('),  # await function()
            re.compile(r'new\s+(\w+)\('),    # new Class()
        ]
        for pattern in call_patterns:
            matches = pattern.findall(content)
            if isinstance(matches[0], tuple):
                context.external_calls.extend([m[1] for m in matches])
            else:
                context.external_calls.extend(matches)
    
    def _extract_csharp_elements(self, content: str, context: FileContext):
        """Extract C# elements"""
        # Classes
        class_pattern = re.compile(r'(?:public|private|internal|protected)?\s*(?:partial\s+)?(?:static\s+)?class\s+(\w+)')
        context.class_definitions.extend(class_pattern.findall(content))
        
        # Interfaces
        interface_pattern = re.compile(r'(?:public|private|internal)?\s*interface\s+(\w+)')
        context.class_definitions.extend(interface_pattern.findall(content))
        
        # Methods
        method_pattern = re.compile(r'(?:public|private|protected|internal)?\s*(?:static\s+)?(?:async\s+)?(?:\w+\s+)?(\w+)\s*\(')
        methods = method_pattern.findall(content)
        context.function_definitions.extend([m for m in methods if m[0].isupper()])
    
    def _extract_java_elements(self, content: str, context: FileContext):
        """Extract Java elements"""
        # Similar to C# but with Java-specific patterns
        class_pattern = re.compile(r'(?:public|private|protected)?\s*(?:final\s+)?(?:abstract\s+)?class\s+(\w+)')
        context.class_definitions.extend(class_pattern.findall(content))
        
        interface_pattern = re.compile(r'(?:public|private)?\s*interface\s+(\w+)')
        context.class_definitions.extend(interface_pattern.findall(content))
        
        method_pattern = re.compile(r'(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:\w+\s+)?(\w+)\s*\(')
        context.function_definitions.extend(method_pattern.findall(content))
    
    def _extract_go_elements(self, content: str, context: FileContext):
        """Extract Go elements"""
        # Functions
        func_pattern = re.compile(r'func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(')
        context.function_definitions.extend(func_pattern.findall(content))
        
        # Types
        type_pattern = re.compile(r'type\s+(\w+)\s+(?:struct|interface)')
        context.class_definitions.extend(type_pattern.findall(content))
        
        # Exported functions (start with capital letter)
        for func in context.function_definitions:
            if func[0].isupper():
                context.exports.append(func)
    
    def _extract_with_regex(self, content: str, context: FileContext):
        """Fallback regex extraction for any language"""
        # Generic class pattern
        class_patterns = [
            re.compile(r'class\s+(\w+)'),
            re.compile(r'interface\s+(\w+)'),
            re.compile(r'struct\s+(\w+)'),
        ]
        for pattern in class_patterns:
            context.class_definitions.extend(pattern.findall(content))
        
        # Generic function pattern
        func_patterns = [
            re.compile(r'(?:def|function|func)\s+(\w+)'),
            re.compile(r'(\w+)\s*:\s*function'),
            re.compile(r'(\w+)\s*=\s*function'),
        ]
        for pattern in func_patterns:
            context.function_definitions.extend(pattern.findall(content))
    
    def _extract_config_elements(self, content: str, context: FileContext):
        """Extract configuration elements"""
        # Try to parse as JSON
        try:
            data = json.loads(content)
            self._extract_config_from_dict(data, context)
            return
        except:
            pass
        
        # Try key-value patterns
        kv_patterns = [
            re.compile(r'^(\w+)\s*[:=]\s*(.+)$', re.MULTILINE),
            re.compile(r'^(\w+)=(.+)$', re.MULTILINE),
        ]
        
        for pattern in kv_patterns:
            matches = pattern.findall(content)
            for key, value in matches:
                context.config_values[key] = value.strip('"\'')
    
    def _extract_config_from_dict(self, data: dict, context: FileContext, prefix: str = ''):
        """Recursively extract config from dictionary"""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                self._extract_config_from_dict(value, context, full_key)
            elif isinstance(value, (str, int, float, bool)):
                context.config_values[full_key] = value
                
                # Check for environment variable references
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    context.environment_vars.append(env_var)
    
    def _extract_build_elements(self, content: str, context: FileContext):
        """Extract build-related elements"""
        # Build commands
        for pattern in self.build_patterns:
            matches = pattern.findall(content)
            for match in matches:
                if isinstance(match, tuple):
                    context.build_commands.append(' '.join(match))
                else:
                    context.build_commands.append(match)
        
        # Script references
        script_patterns = [
            re.compile(r'[\'"]scripts[\'"]:\s*{([^}]+)}', re.DOTALL),
            re.compile(r'RUN\s+(.+)$', re.MULTILINE),  # Dockerfile
            re.compile(r'(?:npm|yarn)\s+run\s+(\S+)'),
        ]
        
        for pattern in script_patterns:
            matches = pattern.findall(content)
            context.script_references.extend(matches)
    
    def _extract_doc_elements(self, content: str, context: FileContext):
        """Extract documentation elements"""
        # Code blocks that might contain important examples
        code_block_pattern = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
        code_blocks = code_block_pattern.findall(content)
        
        for lang, code in code_blocks:
            if lang in ['bash', 'shell', 'sh']:
                # Extract commands from code blocks
                for pattern in self.build_patterns:
                    matches = pattern.findall(code)
                    context.build_commands.extend([str(m) for m in matches])
        
        # File references in markdown links
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        links = link_pattern.findall(content)
        for _, target in links:
            if '.' in target and not target.startswith('http'):
                context.file_references.append(target)
    
    def _extract_file_references(self, content: str, context: FileContext):
        """Extract file references"""
        for pattern in self.file_ref_patterns:
            matches = pattern.findall(content)
            context.file_references.extend(matches)
        
        # Remove duplicates and filter
        context.file_references = list(set(f for f in context.file_references if len(f) > 2))
    
    def _extract_urls(self, content: str, context: FileContext):
        """Extract URL references"""
        for pattern in self.url_patterns:
            matches = pattern.findall(content)
            context.url_references.extend(matches)
        
        context.url_references = list(set(context.url_references))
    
    def _extract_database_references(self, content: str, context: FileContext):
        """Extract database references"""
        for pattern in self.db_patterns:
            matches = pattern.findall(content)
            context.database_references.extend(matches)
        
        context.database_references = list(set(context.database_references))
    
    def _extract_environment_vars(self, content: str, context: FileContext):
        """Extract environment variable references"""
        for pattern in self.env_patterns:
            matches = pattern.findall(content)
            context.environment_vars.extend(matches)
        
        context.environment_vars = list(set(context.environment_vars))
    
    def _extract_important_comments(self, content: str, context: FileContext):
        """Extract important comments and TODOs"""
        for pattern in self.important_comment_patterns:
            matches = pattern.findall(content)
            for match in matches:
                if isinstance(match, tuple):
                    tag, comment = match
                    if tag.upper() == 'TODO':
                        context.todos.append(comment.strip())
                    else:
                        context.important_comments.append(f"{tag}: {comment.strip()}")
                else:
                    context.important_comments.append(match)
    
    def _extract_test_elements(self, content: str, context: FileContext):
        """Extract test-specific elements"""
        for pattern in self.test_patterns:
            matches = pattern.findall(content)
            context.test_dependencies.extend(matches)
        
        # Look for fixture definitions
        fixture_patterns = [
            re.compile(r'@pytest\.fixture\s*\n\s*def\s+(\w+)'),
            re.compile(r'(?:beforeEach|beforeAll|setUp)\s*\('),
            re.compile(r'(?:mock|stub|spy)\s*\('),
        ]
        
        for pattern in fixture_patterns:
            matches = pattern.findall(content)
            if matches:
                context.test_fixtures.extend(matches)