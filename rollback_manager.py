"""
Rollback Manager - Handles safe rollback of file operations
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

from migration_tracker import MigrationTracker

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages rollback operations with verification"""
    
    def __init__(self, migration_tracker: MigrationTracker, work_dir: Path):
        self.migration_tracker = migration_tracker
        self.work_dir = Path(work_dir)
        self.rollback_log_path = self.work_dir / 'rollback_log.json'
        self.rollback_history = self._load_rollback_history()
    
    def _load_rollback_history(self) -> List[Dict]:
        """Load rollback history"""
        if self.rollback_log_path.exists():
            try:
                with open(self.rollback_log_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load rollback history: {e}")
                return []
        return []
    
    def create_rollback_point(self, description: str) -> str:
        """Create a rollback point before operations"""
        rollback_id = datetime.now().strftime('%Y%m%d_%H%M%S_rollback')
        
        rollback_point = {
            'id': rollback_id,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'project_state': self._capture_project_state(),
            'status': 'active'
        }
        
        # Save rollback point
        rollback_file = self.work_dir / f'rollback_{rollback_id}.json'
        with open(rollback_file, 'w') as f:
            json.dump(rollback_point, f, indent=2)
        
        logger.info(f"Created rollback point: {rollback_id}")
        return rollback_id
    
    def rollback_to_point(self, rollback_id: str, verify: bool = True) -> Tuple[bool, List[str]]:
        """Rollback to a specific point"""
        logger.info(f"Starting rollback to point: {rollback_id}")
        errors = []
        
        # Load rollback point
        rollback_file = self.work_dir / f'rollback_{rollback_id}.json'
        if not rollback_file.exists():
            error_msg = f"Rollback point not found: {rollback_id}"
            logger.error(error_msg)
            return False, [error_msg]
        
        with open(rollback_file, 'r') as f:
            rollback_point = json.load(f)
        
        # Start rollback transaction
        self.migration_tracker.start_transaction(f"Rollback to {rollback_id}")
        
        try:
            # Get all migrations after this rollback point
            migrations_to_reverse = self._get_migrations_after(rollback_point['created_at'])
            
            logger.info(f"Found {len(migrations_to_reverse)} operations to reverse")
            
            # Reverse migrations in reverse order
            for migration in reversed(migrations_to_reverse):
                try:
                    self._reverse_migration(migration)
                except Exception as e:
                    error_msg = f"Failed to reverse migration: {migration['source_path']} - {e}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
            
            # Verify state if requested
            if verify:
                verification_errors = self._verify_rollback(rollback_point)
                errors.extend(verification_errors)
            
            # Record rollback
            self._record_rollback(rollback_id, len(errors) == 0, errors)
            
            # Commit transaction
            self.migration_tracker.commit_transaction()
            
            success = len(errors) == 0
            logger.info(f"Rollback {'completed successfully' if success else 'completed with errors'}")
            
            return success, errors
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}", exc_info=True)
            errors.append(f"Rollback failed: {str(e)}")
            return False, errors
    
    def _capture_project_state(self) -> Dict:
        """Capture current project state for verification"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'files': {},
            'directories': []
        }
        
        # This would be enhanced to capture more complete state
        # For now, we rely on the migration tracker's records
        
        return state
    
    def _get_migrations_after(self, timestamp: str) -> List[Dict]:
        """Get all migrations after a specific timestamp"""
        migrations = []
        for migration in self.migration_tracker.migrations:
            if migration.get('timestamp', '') > timestamp:
                migrations.append(migration)
        return migrations
    
    def _reverse_migration(self, migration: Dict):
        """Reverse a single migration"""
        operation = migration['operation']
        source_path = Path(migration['source_path'])
        dest_path = Path(migration['dest_path']) if migration.get('dest_path') else None
        
        logger.info(f"Reversing {operation}: {source_path}")
        
        if operation == 'archive' or operation == 'move':
            if dest_path and dest_path.exists():
                # Ensure source directory exists
                source_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move file back
                shutil.move(str(dest_path), str(source_path))
                
                # Restore metadata
                self._restore_file_metadata(source_path, migration)
                
                # Track the reverse operation
                self.migration_tracker.track_migration(
                    dest_path, source_path, 'rollback_move',
                    f"Rollback of {operation}", {'original_migration': migration}
                )
                
            else:
                raise FileNotFoundError(f"Destination file not found for rollback: {dest_path}")
        
        elif operation == 'delete':
            # Check if we have an archive copy
            if migration.get('archive_path'):
                archive_path = Path(migration['archive_path'])
                if archive_path.exists():
                    source_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(archive_path), str(source_path))
                    
                    self.migration_tracker.track_migration(
                        archive_path, source_path, 'rollback_restore',
                        'Rollback of delete', {'original_migration': migration}
                    )
                else:
                    raise FileNotFoundError(f"No archive found for deleted file: {source_path}")
            else:
                logger.warning(f"Cannot rollback delete - no archive: {source_path}")
        
        elif operation == 'consolidate':
            # Handle document consolidation reversal
            self._reverse_consolidation(migration)
    
    def _restore_file_metadata(self, file_path: Path, migration: Dict):
        """Restore file metadata from migration record"""
        try:
            # Restore modification time
            if migration.get('file_modified'):
                mtime = datetime.fromisoformat(migration['file_modified']).timestamp()
                os.utime(file_path, (mtime, mtime))
            
            # Restore permissions
            if migration.get('file_permissions'):
                os.chmod(file_path, migration['file_permissions'])
                
        except Exception as e:
            logger.warning(f"Could not fully restore metadata for {file_path}: {e}")
    
    def _reverse_consolidation(self, migration: Dict):
        """Reverse a document consolidation"""
        # This would need to extract the original files from the consolidated document
        # For now, we assume consolidations are tracked with enough detail to reverse
        
        consolidated_file = Path(migration['dest_path'])
        original_files = migration.get('metadata', {}).get('original_files', [])
        
        for original in original_files:
            original_path = Path(original['path'])
            original_content = original.get('content')
            
            if original_content:
                original_path.parent.mkdir(parents=True, exist_ok=True)
                with open(original_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                logger.info(f"Restored original file: {original_path}")
    
    def _verify_rollback(self, rollback_point: Dict) -> List[str]:
        """Verify the rollback was successful"""
        errors = []
        
        # Verify all migrations were reversed
        issues = self.migration_tracker.verify_migration_integrity()
        for issue in issues:
            if issue['type'] == 'source_not_removed':
                # This is expected after rollback
                continue
            errors.append(issue['message'])
        
        # Additional verification could include:
        # - Checking file hashes match pre-operation state
        # - Verifying directory structure
        # - Running tests to ensure functionality
        
        return errors
    
    def _record_rollback(self, rollback_id: str, success: bool, errors: List[str]):
        """Record rollback operation"""
        rollback_record = {
            'rollback_id': rollback_id,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'errors': errors,
            'migrations_reversed': len(self._get_migrations_after(
                self._load_rollback_point(rollback_id)['created_at']
            ))
        }
        
        self.rollback_history.append(rollback_record)
        self._save_rollback_history()
    
    def _load_rollback_point(self, rollback_id: str) -> Dict:
        """Load a rollback point"""
        rollback_file = self.work_dir / f'rollback_{rollback_id}.json'
        with open(rollback_file, 'r') as f:
            return json.load(f)
    
    def _save_rollback_history(self):
        """Save rollback history"""
        with open(self.rollback_log_path, 'w') as f:
            json.dump(self.rollback_history, f, indent=2)
    
    def list_rollback_points(self) -> List[Dict]:
        """List available rollback points"""
        rollback_points = []
        
        for file in self.work_dir.glob('rollback_*.json'):
            try:
                with open(file, 'r') as f:
                    point = json.load(f)
                    rollback_points.append({
                        'id': point['id'],
                        'description': point['description'],
                        'created_at': point['created_at'],
                        'status': point.get('status', 'unknown')
                    })
            except Exception as e:
                logger.error(f"Failed to load rollback point {file}: {e}")
        
        return sorted(rollback_points, key=lambda x: x['created_at'], reverse=True)
    
    def cleanup_old_rollback_points(self, days_to_keep: int = 30):
        """Clean up old rollback points"""
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 86400)
        cleaned = 0
        
        for file in self.work_dir.glob('rollback_*.json'):
            try:
                if file.stat().st_mtime < cutoff_date:
                    file.unlink()
                    cleaned += 1
            except Exception as e:
                logger.error(f"Failed to clean up {file}: {e}")
        
        logger.info(f"Cleaned up {cleaned} old rollback points")
        return cleaned
