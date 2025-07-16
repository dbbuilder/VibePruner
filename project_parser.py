"""
Project Parser - Parses project files to identify required dependencies
Supports: .sln, .csproj, package.json, requirements.txt, pyproject.toml, etc.
"""

import os
import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ProjectParser:
    """Parses project files to identify required files"""
    
    def __init__(self, config):
        self.config = config
        self.parsers = {
            '.sln': self._parse_solution,
            '.csproj': self._parse_csproj,
            '.vbproj': self._parse_csproj,  # Same format as csproj
            '.fsproj': self._parse_csproj,  # Same format as csproj
            'package.json': self._parse_package_json,
            'requirements.txt': self._parse_requirements_txt,
            'pyproject.toml': self._parse_pyproject_toml,
            'setup.py': self._parse_setup_py,
            'Cargo.toml': self._parse_cargo_toml,
            'go.mod': self._parse_go_mod,
            'pom.xml': self._parse_pom_xml,
            'build.gradle': self._parse_gradle,
            'CMakeLists.txt': self._parse_cmake,
            'Makefile': self._parse_makefile
        }
    
    def parse_project(self, project_path):
        """Parse all project files in the directory"""
        project_path = Path(project_path)
        analysis = {
            'project_files': [],
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {},
            'project_type': self._detect_project_type(project_path)
        }
        
        # Find and parse all project files
        for filename, parser in self.parsers.items():
            if filename.startswith('.'):
                # Extension-based search
                for file in project_path.rglob(f'*{filename}'):
                    self._parse_file(file, parser, analysis, project_path)
            else:
                # Exact filename search
                for file in project_path.rglob(filename):
                    self._parse_file(file, parser, analysis, project_path)
        
        # Add project files themselves as required
        for proj_file in analysis['project_files']:
            analysis['required_files'].add(proj_file)
        
        # Convert sets to lists for JSON serialization
        analysis['required_files'] = list(analysis['required_files'])
        analysis['entry_points'] = list(analysis['entry_points'])
        analysis['build_files'] = list(analysis['build_files'])
        
        return analysis
    
    def _parse_file(self, file_path, parser, analysis, project_path):
        """Parse a single project file"""
        try:
            relative_path = file_path.relative_to(project_path)
            logger.info(f"Parsing project file: {relative_path}")
            
            analysis['project_files'].append(str(relative_path))
            result = parser(file_path, project_path)
            
            # Merge results
            analysis['required_files'].update(result.get('required_files', []))
            analysis['entry_points'].update(result.get('entry_points', []))
            analysis['build_files'].update(result.get('build_files', []))
            
            # Update dependencies
            deps = result.get('dependencies', {})
            for dep_type, dep_list in deps.items():
                if dep_type not in analysis['dependencies']:
                    analysis['dependencies'][dep_type] = []
                analysis['dependencies'][dep_type].extend(dep_list)
                
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
    
    def _detect_project_type(self, project_path):
        """Detect the primary project type"""
        indicators = {
            'dotnet': ['*.sln', '*.csproj'],
            'node': ['package.json', 'package-lock.json'],
            'python': ['requirements.txt', 'setup.py', 'pyproject.toml'],
            'java': ['pom.xml', 'build.gradle'],
            'go': ['go.mod'],
            'rust': ['Cargo.toml'],
            'cpp': ['CMakeLists.txt', 'Makefile']
        }
        
        for proj_type, patterns in indicators.items():
            for pattern in patterns:
                if list(project_path.glob(pattern)):
                    return proj_type
        
        return 'unknown'
    
    def _parse_solution(self, sln_path, project_path):
        """Parse .NET solution file"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {'projects': []}
        }
        
        with open(sln_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # Extract project references
        project_pattern = r'Project\([^)]+\)\s*=\s*"[^"]+",\s*"([^"]+)"'
        matches = re.findall(project_pattern, content)
        
        for project_ref in matches:
            # Resolve relative to solution file
            full_path = (sln_path.parent / project_ref).resolve()
            if full_path.exists():
                relative = full_path.relative_to(project_path)
                result['required_files'].add(str(relative))
                result['dependencies']['projects'].append(str(relative))
        
        result['build_files'].add(str(sln_path.relative_to(project_path)))
        
        return result
    
    def _parse_csproj(self, csproj_path, project_path):
        """Parse .NET project file"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {'packages': [], 'projects': []}
        }
        
        try:
            tree = ET.parse(csproj_path)
            root = tree.getroot()
            
            # Handle both old and new csproj formats
            # New format (SDK-style)
            for item in root.findall('.//Compile'):
                include = item.get('Include')
                if include:
                    file_path = (csproj_path.parent / include).resolve()
                    if file_path.exists():
                        result['required_files'].add(str(file_path.relative_to(project_path)))
            
            # Content files
            for item in root.findall('.//Content'):
                include = item.get('Include')
                if include:
                    file_path = (csproj_path.parent / include).resolve()
                    if file_path.exists():
                        result['required_files'].add(str(file_path.relative_to(project_path)))
            
            # Entry points (Program.cs, Startup.cs, etc.)
            for pattern in ['Program.cs', 'Startup.cs', 'App.xaml.cs', 'Global.asax.cs']:
                entry_point = csproj_path.parent / pattern
                if entry_point.exists():
                    result['entry_points'].add(str(entry_point.relative_to(project_path)))
            
            # Package references
            for pkg in root.findall('.//PackageReference'):
                include = pkg.get('Include')
                if include:
                    result['dependencies']['packages'].append(include)
            
            # Project references
            for proj in root.findall('.//ProjectReference'):
                include = proj.get('Include')
                if include:
                    proj_path = (csproj_path.parent / include).resolve()
                    if proj_path.exists():
                        result['required_files'].add(str(proj_path.relative_to(project_path)))
                        result['dependencies']['projects'].append(str(proj_path.relative_to(project_path)))
            
        except Exception as e:
            logger.error(f"Error parsing {csproj_path}: {e}")
        
        result['build_files'].add(str(csproj_path.relative_to(project_path)))
        return result
    
    def _parse_package_json(self, package_path, project_path):
        """Parse Node.js package.json"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {'npm': [], 'dev': []}
        }
        
        with open(package_path, 'r') as f:
            data = json.load(f)
        
        # Entry points
        if 'main' in data:
            main_file = (package_path.parent / data['main']).resolve()
            if main_file.exists():
                result['entry_points'].add(str(main_file.relative_to(project_path)))
                result['required_files'].add(str(main_file.relative_to(project_path)))
        
        # Scripts might reference files
        scripts = data.get('scripts', {})
        for script_name, script_cmd in scripts.items():
            # Extract file references from scripts
            file_refs = re.findall(r'(?:node|npm|yarn)\s+([^\s]+\.js)', script_cmd)
            for ref in file_refs:
                file_path = (package_path.parent / ref).resolve()
                if file_path.exists():
                    result['required_files'].add(str(file_path.relative_to(project_path)))
        
        # Dependencies
        result['dependencies']['npm'] = list(data.get('dependencies', {}).keys())
        result['dependencies']['dev'] = list(data.get('devDependencies', {}).keys())
        
        # Common entry points
        for entry in ['index.js', 'app.js', 'server.js', 'src/index.js']:
            entry_path = package_path.parent / entry
            if entry_path.exists():
                result['entry_points'].add(str(entry_path.relative_to(project_path)))
        
        # Build files
        result['build_files'].add(str(package_path.relative_to(project_path)))
        
        # Lock file
        lock_file = package_path.parent / 'package-lock.json'
        if lock_file.exists():
            result['build_files'].add(str(lock_file.relative_to(project_path)))
        
        return result
    
    def _parse_requirements_txt(self, req_path, project_path):
        """Parse Python requirements.txt"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {'pip': []}
        }
        
        with open(req_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name
                    pkg = re.split(r'[<>=!]', line)[0].strip()
                    if pkg:
                        result['dependencies']['pip'].append(pkg)
        
        # Look for common Python entry points
        for entry in ['main.py', 'app.py', '__main__.py', 'run.py', 'manage.py']:
            entry_path = req_path.parent / entry
            if entry_path.exists():
                result['entry_points'].add(str(entry_path.relative_to(project_path)))
        
        result['build_files'].add(str(req_path.relative_to(project_path)))
        return result
    
    def _parse_pyproject_toml(self, toml_path, project_path):
        """Parse Python pyproject.toml"""
        result = {
            'required_files': set(),
            'entry_points': set(), 
            'build_files': set(),
            'dependencies': {'pip': []}
        }
        
        # Simple parsing without toml library
        with open(toml_path, 'r') as f:
            content = f.read()
        
        # Extract dependencies section
        deps_match = re.search(r'\[tool\.poetry\.dependencies\](.*?)\[', content, re.DOTALL)
        if deps_match:
            deps_section = deps_match.group(1)
            for line in deps_section.split('\n'):
                if '=' in line:
                    pkg = line.split('=')[0].strip()
                    if pkg and not pkg.startswith('#'):
                        result['dependencies']['pip'].append(pkg)
        
        result['build_files'].add(str(toml_path.relative_to(project_path)))
        return result
    
    def _parse_setup_py(self, setup_path, project_path):
        """Parse Python setup.py"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {'pip': []}
        }
        
        with open(setup_path, 'r') as f:
            content = f.read()
        
        # Extract install_requires
        requires_match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if requires_match:
            requires = requires_match.group(1)
            for line in requires.split(','):
                pkg = line.strip().strip('"\'')
                if pkg:
                    result['dependencies']['pip'].append(pkg)
        
        result['build_files'].add(str(setup_path.relative_to(project_path)))
        return result
    
    def _parse_cargo_toml(self, cargo_path, project_path):
        """Parse Rust Cargo.toml"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {'cargo': []}
        }
        
        # Add src/main.rs or src/lib.rs as entry points
        src_dir = cargo_path.parent / 'src'
        if src_dir.exists():
            for entry in ['main.rs', 'lib.rs']:
                entry_path = src_dir / entry
                if entry_path.exists():
                    result['entry_points'].add(str(entry_path.relative_to(project_path)))
        
        result['build_files'].add(str(cargo_path.relative_to(project_path)))
        return result
    
    def _parse_go_mod(self, go_path, project_path):
        """Parse Go go.mod"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {'go': []}
        }
        
        # Add main.go as entry point
        main_go = go_path.parent / 'main.go'
        if main_go.exists():
            result['entry_points'].add(str(main_go.relative_to(project_path)))
        
        result['build_files'].add(str(go_path.relative_to(project_path)))
        return result
    
    def _parse_pom_xml(self, pom_path, project_path):
        """Parse Maven pom.xml"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {'maven': []}
        }
        
        result['build_files'].add(str(pom_path.relative_to(project_path)))
        return result
    
    def _parse_gradle(self, gradle_path, project_path):
        """Parse Gradle build file"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {'gradle': []}
        }
        
        result['build_files'].add(str(gradle_path.relative_to(project_path)))
        return result
    
    def _parse_cmake(self, cmake_path, project_path):
        """Parse CMakeLists.txt"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {}
        }
        
        result['build_files'].add(str(cmake_path.relative_to(project_path)))
        return result
    
    def _parse_makefile(self, make_path, project_path):
        """Parse Makefile"""
        result = {
            'required_files': set(),
            'entry_points': set(),
            'build_files': set(),
            'dependencies': {}
        }
        
        result['build_files'].add(str(make_path.relative_to(project_path)))
        return result
