"""
Test suite for VibePruner - ensuring reliability and completeness
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import json
import os

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_guardian import TestGuardian
from migration_tracker import MigrationTracker
from rollback_manager import RollbackManager
from session_manager import SessionManager
from audit_logger import AuditLogger, AuditEvent
from config import Config


class TestMigrationTracker:
    """Test migration tracking functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.work_dir = Path(self.temp_dir) / 'work'
        self.work_dir.mkdir()
        self.tracker = MigrationTracker(self.work_dir)
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_track_migration(self):
        """Test basic migration tracking"""
        # Create test file
        source = Path(self.temp_dir) / 'test.txt'
        source.write_text('test content')
        dest = Path(self.temp_dir) / 'archive' / 'test.txt'
        
        # Start transaction
        trans_id = self.tracker.start_transaction('Test migration')
        
        # Track migration
        record = self.tracker.track_migration(
            source, dest, 'archive', 'Test reason'
        )
        
        assert record['source_path'] == str(source)
        assert record['dest_path'] == str(dest)
        assert record['operation'] == 'archive'
        assert record['source_hash'] is not None
        assert record['status'] == 'pending'
    
    def test_complete_migration_with_verification(self):
        """Test migration completion with hash verification"""
        # Create and move file
        source = Path(self.temp_dir) / 'test.txt'
        source.write_text('test content')
        dest = Path(self.temp_dir) / 'archive' / 'test.txt'
        dest.parent.mkdir(exist_ok=True)
        
        trans_id = self.tracker.start_transaction('Test migration')
        record = self.tracker.track_migration(
            source, dest, 'move', 'Test reason'
        )
        
        # Actually move the file
        shutil.move(str(source), str(dest))
        
        # Complete migration
        self.tracker.complete_migration(record, True)
        
        assert record['status'] == 'success'
        assert record['dest_hash'] == record['source_hash']
    
    def test_rollback_transaction(self):
        """Test transaction rollback"""
        # Create files
        source1 = Path(self.temp_dir) / 'file1.txt'
        source2 = Path(self.temp_dir) / 'file2.txt'
        source1.write_text('content1')
        source2.write_text('content2')
        
        archive_dir = Path(self.temp_dir) / 'archive'
        archive_dir.mkdir()
        
        # Start transaction and track migrations
        trans_id = self.tracker.start_transaction('Test rollback')
        
        record1 = self.tracker.track_migration(
            source1, archive_dir / 'file1.txt', 'move', 'Test'
        )
        shutil.move(str(source1), str(archive_dir / 'file1.txt'))
        self.tracker.complete_migration(record1, True)
        
        record2 = self.tracker.track_migration(
            source2, archive_dir / 'file2.txt', 'move', 'Test'
        )
        shutil.move(str(source2), str(archive_dir / 'file2.txt'))
        self.tracker.complete_migration(record2, True)
        
        # Rollback
        success = self.tracker.rollback_transaction()
        
        assert success
        assert source1.exists()
        assert source2.exists()
        assert not (archive_dir / 'file1.txt').exists()
        assert not (archive_dir / 'file2.txt').exists()


class TestSessionManager:
    """Test session management functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.work_dir = Path(self.temp_dir) / 'work'
        self.work_dir.mkdir()
        self.session_mgr = SessionManager(self.work_dir)
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.session_mgr.is_active:
            self.session_mgr.end_session()
        shutil.rmtree(self.temp_dir)
    
    def test_start_new_session(self):
        """Test starting a new session"""
        session = self.session_mgr.start_session('/test/project')
        
        assert session['id'] is not None
        assert session['project_path'] == '/test/project'
        assert session['status'] == 'active'
        assert self.session_mgr.is_active
    
    def test_session_checkpoints(self):
        """Test checkpoint functionality"""
        session = self.session_mgr.start_session('/test/project')
        
        # Add checkpoints
        self.session_mgr.add_checkpoint('test1', {'data': 'value1'})
        self.session_mgr.add_checkpoint('test2', {'data': 'value2'})
        
        # Retrieve checkpoints
        last = self.session_mgr.get_last_checkpoint()
        assert last['name'] == 'test2'
        
        specific = self.session_mgr.get_last_checkpoint('test1')
        assert specific['data']['data'] == 'value1'
    
    def test_session_recovery(self):
        """Test session recovery after interruption"""
        # Start session
        session1 = self.session_mgr.start_session('/test/project')
        session_id = session1['id']
        
        # Add some data
        self.session_mgr.update_phase('testing')
        self.session_mgr.add_checkpoint('progress', {'files_done': 50})
        
        # Simulate crash (don't properly end session)
        self.session_mgr.is_active = False
        
        # Create new session manager and resume
        new_session_mgr = SessionManager(self.work_dir)
        session2 = new_session_mgr.start_session('/test/project', session_id)
        
        assert session2['id'] == session_id
        assert session2['phase'] == 'testing'
        assert len(session2['checkpoints']) == 1


class TestAuditLogger:
    """Test audit logging functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.work_dir = Path(self.temp_dir) / 'work'
        self.work_dir.mkdir()
        self.audit = AuditLogger(self.work_dir)
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_log_event(self):
        """Test basic event logging"""
        self.audit.log_event(
            AuditEvent.FILE_OPERATION,
            "Test operation",
            {'file': 'test.txt'},
            'testuser'
        )
        
        # Verify log file exists
        assert any(self.audit.audit_dir.glob('audit_*.jsonl'))
        
        # Read and verify entry
        log_file = list(self.audit.audit_dir.glob('audit_*.jsonl'))[0]
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Skip header
            entry = json.loads(lines[-1])
            
            assert entry['event_type'] == 'file_operation'
            assert entry['description'] == 'Test operation'
            assert entry['details']['file'] == 'test.txt'
    
    def test_audit_integrity_verification(self):
        """Test audit log integrity verification"""
        # Log some events
        for i in range(5):
            self.audit.log_event(
                AuditEvent.FILE_OPERATION,
                f"Operation {i}",
                {'index': i}
            )
        
        # Verify integrity
        issues = self.audit.verify_audit_integrity()
        assert len(issues) == 0
        
        # Tamper with log
        log_file = list(self.audit.audit_dir.glob('audit_*.jsonl'))[0]
        with open(log_file, 'a') as f:
            f.write('invalid json line\n')
        
        # Verify again - should find issue
        issues = self.audit.verify_audit_integrity()
        assert len(issues) > 0
        assert issues[0]['issue'] == 'invalid_json'


class TestRollbackManager:
    """Test rollback functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.work_dir = Path(self.temp_dir) / 'work'
        self.work_dir.mkdir()
        
        self.tracker = MigrationTracker(self.work_dir)
        self.rollback = RollbackManager(self.tracker, self.work_dir)
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_create_rollback_point(self):
        """Test rollback point creation"""
        rollback_id = self.rollback.create_rollback_point('Test point')
        
        assert rollback_id is not None
        
        # Verify rollback file exists
        rollback_file = self.work_dir / f'rollback_{rollback_id}.json'
        assert rollback_file.exists()
    
    def test_rollback_to_point(self):
        """Test rolling back to a specific point"""
        # Create initial state
        file1 = Path(self.temp_dir) / 'file1.txt'
        file1.write_text('original content')
        
        # Create rollback point
        rollback_id = self.rollback.create_rollback_point('Before changes')
        
        # Make changes
        archive_dir = Path(self.temp_dir) / 'archive'
        archive_dir.mkdir()
        
        trans_id = self.tracker.start_transaction('Test changes')
        record = self.tracker.track_migration(
            file1, archive_dir / 'file1.txt', 'move', 'Test'
        )
        shutil.move(str(file1), str(archive_dir / 'file1.txt'))
        self.tracker.complete_migration(record, True)
        self.tracker.commit_transaction()
        
        # Verify file was moved
        assert not file1.exists()
        assert (archive_dir / 'file1.txt').exists()
        
        # Rollback
        success, errors = self.rollback.rollback_to_point(rollback_id)
        
        assert success
        assert len(errors) == 0
        assert file1.exists()
        assert file1.read_text() == 'original content'


class TestTestGuardian:
    """Test the test protection functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / 'project'
        self.project_dir.mkdir()
        
        self.config = Config()
        self.guardian = TestGuardian(self.config)
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_discover_python_tests(self):
        """Test Python test discovery"""
        # Create test files
        test_file = self.project_dir / 'test_example.py'
        test_file.write_text('''
def test_something():
    assert True
''')
        
        # Create pytest.ini
        pytest_ini = self.project_dir / 'pytest.ini'
        pytest_ini.write_text('[pytest]\n')
        
        # Discover tests
        tests = self.guardian._discover_tests(self.project_dir)
        
        assert len(tests) > 0
        assert any(t['type'] == 'python' for t in tests)
    
    def test_normalize_output(self):
        """Test output normalization"""
        output = '''
        Test run at 2024-01-15 10:30:45
        File: C:\\Users\\test\\project\\file.py
        Memory address: 0x7f8b8c0d0e10
        Duration: 1.234s
        Test Run abc123def456
        '''
        
        normalized = self.guardian._normalize_output(output)
        
        assert '[TIMESTAMP]' in normalized
        assert '[DURATION]' in normalized
        assert '[ADDRESS]' in normalized
        assert 'Test Run [ID]' in normalized
        assert 'C:\\Users\\test\\project\\' not in normalized
    
    def test_extract_test_metrics(self):
        """Test extraction of test metrics"""
        output = '''
        ============================= test session starts ==============================
        collected 15 tests
        
        tests/test_example.py::test_one PASSED                                   [ 6%]
        tests/test_example.py::test_two PASSED                                   [13%]
        tests/test_example.py::test_three FAILED                                 [20%]
        
        =================================== FAILURES ===================================
        _________________________________ test_three __________________________________
        
        AssertionError: Test failed
        
        ========================= 1 failed, 14 passed in 1.23s =========================
        '''
        
        test_count = self.guardian._extract_test_count(output)
        passed_count = self.guardian._extract_passed_count(output)
        failed_count = self.guardian._extract_failed_count(output)
        
        assert test_count == 15
        assert passed_count == 14
        assert failed_count == 1


def test_integration_scenario():
    """Test a complete integration scenario"""
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Set up project structure
        project_dir = Path(temp_dir) / 'test_project'
        project_dir.mkdir()
        
        # Create some files
        src_dir = project_dir / 'src'
        src_dir.mkdir()
        
        main_file = src_dir / 'main.py'
        main_file.write_text('print("Hello")')
        
        temp_file = src_dir / 'temp.txt'
        temp_file.write_text('temporary data')
        
        # Create work directory
        work_dir = project_dir / '.vibepruner'
        work_dir.mkdir()
        
        # Initialize components
        tracker = MigrationTracker(work_dir)
        rollback = RollbackManager(tracker, work_dir)
        session = SessionManager(work_dir)
        audit = AuditLogger(work_dir)
        
        # Start session
        sess = session.start_session(str(project_dir))
        
        # Create rollback point
        rollback_id = rollback.create_rollback_point('Initial state')
        
        # Track and execute migration
        trans_id = tracker.start_transaction('Clean temp files')
        
        archive_dir = project_dir / '.archive'
        archive_dir.mkdir()
        
        record = tracker.track_migration(
            temp_file,
            archive_dir / 'temp.txt',
            'archive',
            'Temporary file'
        )
        
        # Log the operation
        audit.log_file_operation(
            'archive',
            temp_file,
            archive_dir / 'temp.txt'
        )
        
        # Move file
        shutil.move(str(temp_file), str(archive_dir / 'temp.txt'))
        tracker.complete_migration(record, True)
        
        # Verify migration
        assert not temp_file.exists()
        assert (archive_dir / 'temp.txt').exists()
        
        # End session
        session.end_session('completed')
        
        # Verify audit trail
        report = audit.generate_audit_report()
        assert report['summary']['total_events'] > 0
        assert report['file_operations']['total'] == 1
        
    finally:
        shutil.rmtree(temp_dir)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
