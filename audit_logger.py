"""
Audit Logger - Comprehensive audit trail for compliance and tracking
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import threading
from enum import Enum

logger = logging.getLogger(__name__)


class AuditEvent(Enum):
    """Types of audit events"""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    FILE_SCAN = "file_scan"
    FILE_ANALYZE = "file_analyze"
    PROPOSAL_GENERATE = "proposal_generate"
    USER_DECISION = "user_decision"
    FILE_OPERATION = "file_operation"
    TEST_RUN = "test_run"
    TEST_COMPARE = "test_compare"
    ROLLBACK = "rollback"
    ERROR = "error"
    WARNING = "warning"
    CONFIG_CHANGE = "config_change"
    PERMISSION_CHECK = "permission_check"


class AuditLogger:
    """Provides comprehensive audit logging with integrity protection"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = Path(work_dir)
        self.audit_dir = self.work_dir / 'audit'
        self.audit_dir.mkdir(exist_ok=True)
        
        # Current audit log file
        self.current_log_file = self._get_current_log_file()
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Audit configuration
        self.config = {
            'include_checksums': True,
            'include_user_info': True,
            'include_system_info': True,
            'max_log_size_mb': 100,
            'retention_days': 365
        }
        
        # Initialize audit log
        self._initialize_audit_log()
    
    def _get_current_log_file(self) -> Path:
        """Get current audit log file path"""
        date_str = datetime.now().strftime('%Y%m%d')
        return self.audit_dir / f'audit_{date_str}.jsonl'    
    def _initialize_audit_log(self):
        """Initialize audit log with header"""
        if not self.current_log_file.exists():
            header = {
                'type': 'audit_log_header',
                'version': '1.0',
                'created_at': datetime.now().isoformat(),
                'system_info': self._get_system_info()
            }
            self._write_audit_entry(header)
    
    def log_event(self, 
                  event_type: AuditEvent,
                  description: str,
                  details: Optional[Dict] = None,
                  user: Optional[str] = None,
                  severity: str = 'info'):
        """Log an audit event"""
        
        audit_entry = {
            'id': self._generate_event_id(),
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type.value,
            'description': description,
            'severity': severity,
            'details': details or {},
            'context': self._get_context(user)
        }
        
        # Add integrity checksum
        if self.config['include_checksums']:
            audit_entry['checksum'] = self._calculate_checksum(audit_entry)
        
        self._write_audit_entry(audit_entry)
        
        # Also log to standard logger
        log_method = getattr(logger, severity, logger.info)
        log_method(f"AUDIT: {event_type.value} - {description}")    
    def log_file_operation(self,
                          operation: str,
                          source_path: Path,
                          dest_path: Optional[Path] = None,
                          result: str = 'success',
                          error: Optional[str] = None,
                          metadata: Optional[Dict] = None):
        """Log a file operation with full details"""
        
        details = {
            'operation': operation,
            'source_path': str(source_path),
            'source_exists': source_path.exists(),
            'result': result
        }
        
        if dest_path:
            details['dest_path'] = str(dest_path)
            details['dest_exists'] = dest_path.exists()
        
        if error:
            details['error'] = error
        
        if metadata:
            details['metadata'] = metadata
        
        # Add file details if exists
        if source_path.exists():
            try:
                stat = source_path.stat()
                details['file_info'] = {
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'permissions': oct(stat.st_mode)
                }
                
                # Add file hash for important operations
                if operation in ['move', 'delete', 'archive']:
                    details['file_hash'] = self._calculate_file_hash(source_path)
                    
            except Exception as e:
                details['file_info_error'] = str(e)
        
        self.log_event(
            AuditEvent.FILE_OPERATION,
            f"{operation} operation on {source_path.name}",
            details,
            severity='warning' if result != 'success' else 'info'
        )    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = datetime.now().isoformat()
        random_component = os.urandom(8).hex()
        return f"{timestamp}-{random_component}"
    
    def _get_context(self, user: Optional[str] = None) -> Dict:
        """Get current context information"""
        context = {
            'process_id': os.getpid(),
            'working_directory': os.getcwd()
        }
        
        if self.config['include_user_info']:
            context['user'] = user or os.environ.get('USER', 'unknown')
            context['hostname'] = os.environ.get('COMPUTERNAME', 'unknown')
        
        if self.config['include_system_info']:
            context['python_version'] = self._get_python_version()
        
        return context
    
    def _get_system_info(self) -> Dict:
        """Get system information"""
        import platform
        import sys
        
        return {
            'platform': platform.platform(),
            'python_version': sys.version,
            'hostname': platform.node(),
            'architecture': platform.machine()
        }
    
    def _get_python_version(self) -> str:
        """Get Python version string"""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    def _calculate_checksum(self, data: Dict) -> str:
        """Calculate checksum for audit entry"""
        # Remove checksum field if present
        data_copy = data.copy()
        data_copy.pop('checksum', None)
        
        # Convert to stable string representation
        data_str = json.dumps(data_copy, sort_keys=True)
        
        # Calculate SHA256
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _write_audit_entry(self, entry: Dict):
        """Write audit entry to log file"""
        with self.lock:
            # Check if we need to rotate log file
            if self._should_rotate_log():
                self._rotate_log_file()
            
            # Write entry as JSON line
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write('\n')
    
    def _should_rotate_log(self) -> bool:
        """Check if log file should be rotated"""
        if not self.current_log_file.exists():
            return False
        
        # Check file size
        size_mb = self.current_log_file.stat().st_size / (1024 * 1024)
        if size_mb > self.config['max_log_size_mb']:
            return True
        
        # Check date (rotate daily)
        current_date = datetime.now().strftime('%Y%m%d')
        if current_date not in self.current_log_file.name:
            return True
        
        return False    
    def log_error(self,
                  error_message: str,
                  error_type: str,
                  stack_trace: Optional[str] = None,
                  context: Optional[Dict] = None):
        """Log an error with full context"""
        
        details = {
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {}
        }
        
        if stack_trace:
            details['stack_trace'] = stack_trace
        
        self.log_event(
            AuditEvent.ERROR,
            f"{error_type}: {error_message[:100]}",
            details,
            severity='error'
        )
    
    def _rotate_log_file(self):
        """Rotate log file"""
        if self.current_log_file.exists():
            # Create archive name
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_name = self.current_log_file.stem + f'_{timestamp}.jsonl'
            archive_path = self.audit_dir / 'archive' / archive_name
            
            # Create archive directory
            archive_path.parent.mkdir(exist_ok=True)
            
            # Move current file to archive
            self.current_log_file.rename(archive_path)
        
        # Update current log file
        self.current_log_file = self._get_current_log_file()
        self._initialize_audit_log()
    
    def generate_audit_report(self, 
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             event_types: Optional[List[AuditEvent]] = None) -> Dict:
        """Generate audit report for specified period"""
        
        report = {
            'period': {
                'start': start_date or 'beginning',
                'end': end_date or 'current'
            },
            'summary': {
                'total_events': 0,
                'events_by_type': {},
                'events_by_severity': {},
                'errors': 0,
                'warnings': 0
            },
            'file_operations': {
                'total': 0,
                'by_operation': {},
                'failed': 0
            },
            'user_decisions': {
                'total': 0,
                'approved': 0,
                'rejected': 0
            },
            'test_results': {
                'total_runs': 0,
                'passed': 0,
                'failed': 0
            }
        }
        
        # Process audit files
        for log_file in sorted(self.audit_dir.glob('audit_*.jsonl')):
            self._process_log_file_for_report(log_file, report, start_date, end_date, event_types)
        
        return report    
    def log_test_result(self,
                       test_command: str,
                       result: str,
                       duration: float,
                       comparison: Optional[Dict] = None):
        """Log test execution and comparison results"""
        
        details = {
            'test_command': test_command,
            'result': result,
            'duration_seconds': duration
        }
        
        if comparison:
            details['comparison'] = comparison
        
        severity = 'error' if result == 'failed' else 'info'
        
        self.log_event(
            AuditEvent.TEST_RUN if not comparison else AuditEvent.TEST_COMPARE,
            f"Test {'comparison' if comparison else 'execution'}: {test_command}",
            details,
            severity=severity
        )
    
    def log_user_decision(self,
                         file_path: str,
                         proposed_action: str,
                         user_decision: str,
                         user_reason: Optional[str] = None,
                         confidence_score: Optional[float] = None):
        """Log user decision on a proposed action"""
        
        details = {
            'file_path': file_path,
            'proposed_action': proposed_action,
            'user_decision': user_decision,
            'confidence_score': confidence_score
        }
        
        if user_reason:
            details['user_reason'] = user_reason
        
        self.log_event(
            AuditEvent.USER_DECISION,
            f"User {user_decision} {proposed_action} for {Path(file_path).name}",
            details
        )    
    def log_config_change(self,
                         config_key: str,
                         old_value: Any,
                         new_value: Any,
                         changed_by: Optional[str] = None):
        """Log configuration changes"""
        
        details = {
            'config_key': config_key,
            'old_value': old_value,
            'new_value': new_value,
            'changed_by': changed_by or 'system'
        }
        
        self.log_event(
            AuditEvent.CONFIG_CHANGE,
            f"Configuration changed: {config_key}",
            details
        )
    
    def _process_log_file_for_report(self, 
                                    log_file: Path, 
                                    report: Dict,
                                    start_date: Optional[str],
                                    end_date: Optional[str],
                                    event_types: Optional[List[AuditEvent]]):
        """Process a log file for report generation"""
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    
                    # Skip if outside date range
                    entry_date = entry.get('timestamp', '')[:10]
                    if start_date and entry_date < start_date:
                        continue
                    if end_date and entry_date > end_date:
                        continue
                    
                    # Skip if not requested event type
                    if event_types:
                        event_type = entry.get('event_type')
                        if not any(event_type == et.value for et in event_types):
                            continue
                    
                    # Update report statistics
                    self._update_report_stats(report, entry)
                    
                except json.JSONDecodeError:
                    # Skip invalid entries
                    pass
    
    def _update_report_stats(self, report: Dict, entry: Dict):
        """Update report statistics with entry data"""
        
        report['summary']['total_events'] += 1
        
        # Count by event type
        event_type = entry.get('event_type', 'unknown')
        if event_type not in report['summary']['events_by_type']:
            report['summary']['events_by_type'][event_type] = 0
        report['summary']['events_by_type'][event_type] += 1
        
        # Count by severity
        severity = entry.get('severity', 'info')
        if severity not in report['summary']['events_by_severity']:
            report['summary']['events_by_severity'][severity] = 0
        report['summary']['events_by_severity'][severity] += 1
        
        # Update specific counters
        if severity == 'error':
            report['summary']['errors'] += 1
        elif severity == 'warning':
            report['summary']['warnings'] += 1