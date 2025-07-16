"""
Session Manager - Handles session state and recovery from interruptions
"""

import os
import json
import signal
import atexit
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Callable
import logging
import threading
import time

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session state with recovery capabilities"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(exist_ok=True)
        
        self.session_file = self.work_dir / 'current_session.json'
        self.session_lock_file = self.work_dir / 'session.lock'
        self.checkpoint_file = self.work_dir / 'checkpoint.json'
        
        self.session = None
        self.is_active = False
        self.checkpoint_interval = 30  # seconds
        self.checkpoint_thread = None
        self._shutdown_handlers = []
        
        # Register signal handlers
        self._register_signal_handlers()
    
    def start_session(self, project_path: str, resume_session_id: Optional[str] = None) -> Dict:
        """Start a new session or resume an existing one"""
        
        # Check for existing lock
        if self._check_session_lock():
            logger.warning("Another session appears to be active")
            if not self._prompt_takeover():
                raise RuntimeError("Cannot start session - another instance is running")
        
        if resume_session_id:
            # Resume existing session
            self.session = self._load_session(resume_session_id)
            logger.info(f"Resuming session: {resume_session_id}")
        else:
            # Check for abandoned session
            abandoned_session = self._check_abandoned_session()
            if abandoned_session:
                logger.info(f"Found abandoned session: {abandoned_session['id']}")
                if self._prompt_resume():
                    self.session = abandoned_session
                    self.session['resumed_at'] = datetime.now().isoformat()
                else:
                    # Archive the abandoned session
                    self._archive_session(abandoned_session)
                    self.session = self._create_new_session(project_path)
            else:
                self.session = self._create_new_session(project_path)
        
        # Create session lock
        self._create_session_lock()
        
        # Save initial session state
        self._save_session()
        
        # Start checkpoint thread
        self._start_checkpoint_thread()
        
        self.is_active = True
        logger.info(f"Session started: {self.session['id']}")
        
        return self.session
    
    def _create_new_session(self, project_path: str) -> Dict:
        """Create a new session"""
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S_') + os.urandom(4).hex()
        
        return {
            'id': session_id,
            'project_path': project_path,
            'started_at': datetime.now().isoformat(),
            'status': 'active',
            'phase': 'initialization',
            'checkpoints': [],
            'completed_operations': [],
            'pending_operations': [],
            'errors': [],
            'stats': {
                'files_analyzed': 0,
                'files_processed': 0,
                'tests_run': 0,
                'operations_completed': 0
            }
        }
    
    def update_phase(self, phase: str, metadata: Optional[Dict] = None):
        """Update current session phase"""
        if not self.session:
            return
        
        self.session['phase'] = phase
        self.session['phase_updated_at'] = datetime.now().isoformat()
        
        if metadata:
            if 'phase_metadata' not in self.session:
                self.session['phase_metadata'] = {}
            self.session['phase_metadata'][phase] = metadata
        
        self._save_session()
        logger.info(f"Session phase updated: {phase}")
    
    def add_checkpoint(self, name: str, data: Dict):
        """Add a checkpoint for recovery"""
        checkpoint = {
            'name': name,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        self.session['checkpoints'].append(checkpoint)
        
        # Also save to separate checkpoint file for quick access
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        self._save_session()
        logger.debug(f"Checkpoint added: {name}")
    
    def get_last_checkpoint(self, name: Optional[str] = None) -> Optional[Dict]:
        """Get the last checkpoint, optionally filtered by name"""
        if not self.session or not self.session.get('checkpoints'):
            return None
        
        checkpoints = self.session['checkpoints']
        
        if name:
            # Filter by name
            checkpoints = [cp for cp in checkpoints if cp['name'] == name]
        
        return checkpoints[-1] if checkpoints else None
    
    def record_operation(self, operation: Dict, status: str = 'completed'):
        """Record an operation in the session"""
        operation['timestamp'] = datetime.now().isoformat()
        operation['status'] = status
        
        if status == 'completed':
            self.session['completed_operations'].append(operation)
            self.session['stats']['operations_completed'] += 1
        else:
            self.session['pending_operations'].append(operation)
        
        self._save_session()
    
    def record_error(self, error: str, context: Optional[Dict] = None):
        """Record an error in the session"""
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'error': error,
            'phase': self.session.get('phase'),
            'context': context or {}
        }
        
        self.session['errors'].append(error_record)
        self._save_session()
        
        logger.error(f"Session error recorded: {error}")
    
    def update_stats(self, **kwargs):
        """Update session statistics"""
        for key, value in kwargs.items():
            if key in self.session['stats']:
                if isinstance(value, int):
                    self.session['stats'][key] += value
                else:
                    self.session['stats'][key] = value
        
        self._save_session()
    
    def end_session(self, status: str = 'completed'):
        """End the current session"""
        if not self.session:
            return
        
        self.session['ended_at'] = datetime.now().isoformat()
        self.session['status'] = status
        
        # Calculate duration
        start = datetime.fromisoformat(self.session['started_at'])
        end = datetime.now()
        self.session['duration_seconds'] = (end - start).total_seconds()
        
        # Stop checkpoint thread
        self._stop_checkpoint_thread()
        
        # Save final state
        self._save_session()
        
        # Archive session
        self._archive_session(self.session)
        
        # Remove lock
        self._remove_session_lock()
        
        self.is_active = False
        logger.info(f"Session ended: {self.session['id']} - Status: {status}")
        
        self.session = None
    
    def _check_session_lock(self) -> bool:
        """Check if a session lock exists"""
        if not self.session_lock_file.exists():
            return False
        
        try:
            with open(self.session_lock_file, 'r') as f:
                lock_data = json.load(f)
            
            # Check if lock is stale (older than 5 minutes)
            lock_time = datetime.fromisoformat(lock_data['timestamp'])
            if (datetime.now() - lock_time).total_seconds() > 300:
                logger.warning("Found stale session lock")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking session lock: {e}")
            return False
    
    def _create_session_lock(self):
        """Create a session lock file"""
        lock_data = {
            'session_id': self.session['id'],
            'timestamp': datetime.now().isoformat(),
            'pid': os.getpid()
        }
        
        with open(self.session_lock_file, 'w') as f:
            json.dump(lock_data, f)
    
    def _remove_session_lock(self):
        """Remove session lock file"""
        if self.session_lock_file.exists():
            self.session_lock_file.unlink()
    
    def _check_abandoned_session(self) -> Optional[Dict]:
        """Check for abandoned session"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    session = json.load(f)
                
                if session.get('status') == 'active':
                    return session
                    
            except Exception as e:
                logger.error(f"Error loading abandoned session: {e}")
        
        return None
    
    def _prompt_resume(self) -> bool:
        """Prompt user to resume abandoned session"""
        # In a real implementation, this would interact with the UI
        # For now, we'll auto-resume
        return True
    
    def _prompt_takeover(self) -> bool:
        """Prompt user to take over existing session"""
        # In a real implementation, this would interact with the UI
        # For now, we'll auto-takeover stale locks
        return True
    
    def _save_session(self):
        """Save current session state"""
        if not self.session:
            return
        
        try:
            # Write to temporary file first
            temp_file = self.session_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self.session, f, indent=2)
            
            # Atomic replace
            temp_file.replace(self.session_file)
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}", exc_info=True)
    
    def _load_session(self, session_id: str) -> Dict:
        """Load a specific session"""
        # Try current session file first
        if self.session_file.exists():
            with open(self.session_file, 'r') as f:
                session = json.load(f)
                if session['id'] == session_id:
                    return session
        
        # Try archived sessions
        archive_file = self.work_dir / 'sessions' / f'{session_id}.json'
        if archive_file.exists():
            with open(archive_file, 'r') as f:
                return json.load(f)
        
        raise FileNotFoundError(f"Session not found: {session_id}")
    
    def _archive_session(self, session: Dict):
        """Archive a completed session"""
        archive_dir = self.work_dir / 'sessions'
        archive_dir.mkdir(exist_ok=True)
        
        archive_file = archive_dir / f"{session['id']}.json"
        with open(archive_file, 'w') as f:
            json.dump(session, f, indent=2)
        
        # Remove current session file
        if self.session_file.exists():
            self.session_file.unlink()
    
    def _start_checkpoint_thread(self):
        """Start automatic checkpoint thread"""
        def checkpoint_loop():
            while self.is_active:
                time.sleep(self.checkpoint_interval)
                if self.is_active and self.session:
                    self._save_session()
                    logger.debug("Automatic checkpoint saved")
        
        self.checkpoint_thread = threading.Thread(target=checkpoint_loop, daemon=True)
        self.checkpoint_thread.start()
    
    def _stop_checkpoint_thread(self):
        """Stop checkpoint thread"""
        self.is_active = False
        if self.checkpoint_thread:
            self.checkpoint_thread.join(timeout=5)
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, saving session state...")
            if self.session and self.is_active:
                self.session['interrupted'] = True
                self.session['interrupt_signal'] = signum
                self._save_session()
                self._run_shutdown_handlers()
        
        # Register handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register atexit handler
        atexit.register(self._cleanup)
    
    def register_shutdown_handler(self, handler: Callable):
        """Register a handler to be called on shutdown"""
        self._shutdown_handlers.append(handler)
    
    def _run_shutdown_handlers(self):
        """Run all registered shutdown handlers"""
        for handler in self._shutdown_handlers:
            try:
                handler()
            except Exception as e:
                logger.error(f"Error in shutdown handler: {e}")
    
    def _cleanup(self):
        """Cleanup on exit"""
        if self.session and self.is_active:
            logger.info("Performing session cleanup...")
            self.end_session('interrupted')
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session"""
        if not self.session:
            return {}
        
        return {
            'id': self.session['id'],
            'phase': self.session.get('phase'),
            'status': self.session.get('status'),
            'duration': self._calculate_duration(),
            'stats': self.session.get('stats', {}),
            'error_count': len(self.session.get('errors', [])),
            'checkpoint_count': len(self.session.get('checkpoints', []))
        }
    
    def _calculate_duration(self) -> float:
        """Calculate session duration in seconds"""
        if not self.session:
            return 0
        
        start = datetime.fromisoformat(self.session['started_at'])
        end = datetime.now()
        
        if 'ended_at' in self.session:
            end = datetime.fromisoformat(self.session['ended_at'])
        
        return (end - start).total_seconds()
