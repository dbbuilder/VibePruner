"""
Test Guardian - Captures and validates test outputs
Supports: pytest, unittest, dotnet test, npm test, playwright, SQL tests
"""

import os
import re
import json
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TestGuardian:
    """Protects test integrity by capturing and comparing outputs"""
    
    def __init__(self, config):
        self.config = config
        self.test_patterns = {
            'python': {
                'files': ['test_*.py', '*_test.py', '*_tests.py'],
                'commands': ['pytest', 'python -m pytest', 'python -m unittest'],
                'config_files': ['pytest.ini', 'setup.cfg', 'tox.ini']
            },
            'dotnet': {
                'files': ['*Test*.cs', '*Tests*.cs'],
                'commands': ['dotnet test'],
                'config_files': ['*.csproj', '*.sln']
            },
            'javascript': {
                'files': ['*.test.js', '*.spec.js', '*.test.ts', '*.spec.ts'],
                'commands': ['npm test', 'yarn test', 'jest', 'mocha'],
                'config_files': ['package.json', 'jest.config.js']
            },
            'playwright': {
                'files': ['*.spec.js', '*.spec.ts'],
                'commands': ['npx playwright test', 'yarn playwright test'],
                'config_files': ['playwright.config.js', 'playwright.config.ts']
            },
            'sql': {
                'files': ['test_*.sql', '*_test.sql'],
                'commands': ['sqlcmd', 'psql'],
                'config_files': []
            }
        }
    
    def create_baseline(self, project_path):
        """Create baseline of all test outputs"""
        baseline = {
            'project_path': str(project_path),
            'created_at': datetime.now().isoformat(),
            'tests': [],
            'success': True
        }
        
        # Discover test files and commands
        discovered_tests = self._discover_tests(project_path)
        
        # Run each test and capture output
        for test in discovered_tests:
            logger.info(f"Running test: {test['command']} in {test['working_dir']}")
            result = self._run_test(test)
            
            if result:
                # Create fingerprint of output
                result['fingerprint'] = self._create_output_fingerprint(result)
                baseline['tests'].append(result)
            else:
                logger.warning(f"Failed to run test: {test['command']}")
        
        return baseline
    
    def validate_against_baseline(self, project_path, baseline):
        """Validate current test outputs against baseline"""
        validation = {
            'success': True,
            'failed_tests': [],
            'missing_tests': [],
            'comparison_details': []
        }
        
        # Re-run all baseline tests
        for baseline_test in baseline['tests']:
            test_info = {
                'command': baseline_test['command'],
                'working_dir': baseline_test['working_dir']
            }
            
            current_result = self._run_test(test_info)
            
            if not current_result:
                validation['missing_tests'].append(baseline_test['command'])
                validation['success'] = False
                continue
            
            # Compare results
            comparison = self._compare_test_results(baseline_test, current_result)
            validation['comparison_details'].append(comparison)
            
            if not comparison['matches']:
                validation['failed_tests'].append({
                    'command': baseline_test['command'],
                    'reason': comparison['reason']
                })
                validation['success'] = False
        
        return validation
    
    def _discover_tests(self, project_path):
        """Discover all tests in the project"""
        tests = []
        project_path = Path(project_path)
        
        # Check for each test type
        for test_type, patterns in self.test_patterns.items():
            # Look for test files
            test_files = []
            for pattern in patterns['files']:
                test_files.extend(project_path.rglob(pattern))
            
            if test_files:
                logger.info(f"Found {len(test_files)} {test_type} test files")
            
            # Look for test commands in package.json or project files
            if test_type == 'javascript' or test_type == 'playwright':
                package_json = project_path / 'package.json'
                if package_json.exists():
                    with open(package_json, 'r') as f:
                        package_data = json.load(f)
                        scripts = package_data.get('scripts', {})
                        
                        for script_name, script_cmd in scripts.items():
                            if 'test' in script_name.lower():
                                tests.append({
                                    'type': test_type,
                                    'command': f'npm run {script_name}',
                                    'working_dir': str(project_path),
                                    'source': 'package.json'
                                })
            
            elif test_type == 'dotnet':
                # Find all .csproj files with test in name
                for csproj in project_path.rglob('*Test*.csproj'):
                    tests.append({
                        'type': test_type,
                        'command': 'dotnet test',
                        'working_dir': str(csproj.parent),
                        'source': str(csproj)
                    })
            
            elif test_type == 'python':
                # Check for pytest.ini or setup.cfg
                if (project_path / 'pytest.ini').exists() or \
                   (project_path / 'setup.cfg').exists() or \
                   test_files:
                    tests.append({
                        'type': test_type,
                        'command': 'pytest -v',
                        'working_dir': str(project_path),
                        'source': 'pytest discovery'
                    })
        
        return tests
    
    def _run_test(self, test_info):
        """Run a test and capture output"""
        try:
            start_time = datetime.now()
            
            result = subprocess.run(
                test_info['command'],
                shell=True,
                cwd=test_info['working_dir'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                'command': test_info['command'],
                'working_dir': test_info['working_dir'],
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': duration,
                'timestamp': start_time.isoformat()
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Test timed out: {test_info['command']}")
            return None
        except Exception as e:
            logger.error(f"Error running test: {e}")
            return None
    
    def _create_output_fingerprint(self, test_result):
        """Create a fingerprint of test output, ignoring dynamic values"""
        # Combine stdout and stderr
        output = test_result['stdout'] + test_result['stderr']
        
        # Remove common dynamic values
        output = self._normalize_output(output)
        
        # Extract key metrics
        metrics = {
            'exit_code': test_result['exit_code'],
            'test_count': self._extract_test_count(output),
            'passed_count': self._extract_passed_count(output),
            'failed_count': self._extract_failed_count(output),
            'error_signatures': self._extract_error_signatures(output)
        }
        
        # Create hash of normalized output
        output_hash = hashlib.md5(output.encode()).hexdigest()
        
        return {
            'output_hash': output_hash,
            'metrics': metrics,
            'normalized_length': len(output)
        }
    
    def _normalize_output(self, output):
        """Normalize test output by removing dynamic values"""
        # Remove timestamps
        output = re.sub(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}', '[TIMESTAMP]', output)
        output = re.sub(r'\d+(\.\d+)?s', '[DURATION]', output)
        
        # Remove file paths (keep just filename)
        output = re.sub(r'[A-Za-z]:[\\\/][^\s]+[\\\/]([^\s\\\/]+)', r'\1', output)
        output = re.sub(r'\/[^\s]+\/([^\s\/]+)', r'\1', output)
        
        # Remove memory addresses
        output = re.sub(r'0x[0-9a-fA-F]+', '[ADDRESS]', output)
        
        # Remove GUIDs
        output = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '[GUID]', output)
        
        # Remove test run IDs
        output = re.sub(r'Test Run \w+', 'Test Run [ID]', output)
        
        return output
    
    def _extract_test_count(self, output):
        """Extract total test count from output"""
        patterns = [
            r'(\d+) test[s]? ran',
            r'(\d+) test[s]? collected',
            r'Total tests: (\d+)',
            r'(\d+) passed',
            r'Test Count: (\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return -1
    
    def _extract_passed_count(self, output):
        """Extract passed test count"""
        patterns = [
            r'(\d+) passed',
            r'Passed:\s*(\d+)',
            r' (\d+) test[s]?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return -1
    
    def _extract_failed_count(self, output):
        """Extract failed test count"""
        patterns = [
            r'(\d+) failed',
            r'Failed:\s*(\d+)',
            r' (\d+) test[s]?',
            r'(\d+) error[s]?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0
    
    def _extract_error_signatures(self, output):
        """Extract error signatures for comparison"""
        signatures = []
        
        # Common error patterns
        error_patterns = [
            r'AssertionError: (.+)',
            r'Error: (.+)',
            r'FAILED (.+) -',
            r' (.+)',
            r'Test failed: (.+)'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, output)
            signatures.extend(matches)
        
        return signatures
    
    def _compare_test_results(self, baseline, current):
        """Compare two test results"""
        baseline_fp = self._create_output_fingerprint(baseline)
        current_fp = self._create_output_fingerprint(current)
        
        comparison = {
            'matches': True,
            'reason': '',
            'details': {}
        }
        
        # Compare exit codes
        if baseline['exit_code'] != current['exit_code']:
            comparison['matches'] = False
            comparison['reason'] = f"Exit code changed: {baseline['exit_code']} -> {current['exit_code']}"
            return comparison
        
        # Compare test metrics
        baseline_metrics = baseline_fp['metrics']
        current_metrics = current_fp['metrics']
        
        if baseline_metrics['test_count'] != current_metrics['test_count'] and \
           baseline_metrics['test_count'] != -1:  # -1 means couldn't extract
            comparison['matches'] = False
            comparison['reason'] = f"Test count changed: {baseline_metrics['test_count']} -> {current_metrics['test_count']}"
            return comparison
        
        if baseline_metrics['failed_count'] != current_metrics['failed_count']:
            comparison['matches'] = False
            comparison['reason'] = f"Failed test count changed: {baseline_metrics['failed_count']} -> {current_metrics['failed_count']}"
            return comparison
        
        # If we have error signatures, compare them
        if baseline_metrics['error_signatures'] or current_metrics['error_signatures']:
            baseline_errors = set(baseline_metrics['error_signatures'])
            current_errors = set(current_metrics['error_signatures'])
            
            if baseline_errors != current_errors:
                comparison['matches'] = False
                new_errors = current_errors - baseline_errors
                fixed_errors = baseline_errors - current_errors
                
                if new_errors:
                    comparison['reason'] = f"New errors: {list(new_errors)}"
                elif fixed_errors:
                    comparison['reason'] = f"Fixed errors: {list(fixed_errors)}"
        
        return comparison
