"""
Migration Tracker - Tracks all file movements with complete audit trail
"""

import os
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MigrationTracker:
    """Tracks all file migrations with checksums and metadata"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(exist_ok=True)
        
        self.migration_log_path = self.work_dir / 'migration_log.json'
        self.transaction_log_path = self.work_dir / 'transaction_log.json'
        
        self.migrations = self._load_migrations()
        self.current_transaction = None
        
    def _load_migrations(self) -> List[Dict]:
        """Load existing migration log"""
        if self.migration_log_path.exists():
            try:
                with open(self.migration_log_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load migration log: {e}")
                # Create backup and start fresh
                backup_path = self.migration_log_path.with_suffix('.backup')
                shutil.copy2(self.migration_log_path, backup_path)
                return []
        return []
    
    def start_transaction(self, description: str) -> str:
        """Start a new migration transaction"""
        transaction_id = datetime.now().strftime('%Y%m%d_%H%M%S_') + \
                        hashlib.md5(description.encode()).hexdigest()[:8]
        
        self.current_transaction = {
            'id': transaction_id,
            'description': description,
            'start_time': datetime.now().isoformat(),
            'operations': [],
            'status': 'in_progress'
        }
        
        self._save_transaction()
        logger.info(f"Started transaction: {transaction_id} - {description}")
        return transaction_id
    
    def track_migration(self, 
                       source_path: Path,
                       dest_path: Path,
                       operation: str,
                       reason: str,
                       metadata: Optional[Dict] = None) -> Dict:
        """Track a single file migration"""
        try:
            # Ensure paths are absolute
            source_path = Path(source_path).resolve()
            dest_path = Path(dest_path).resolve() if dest_path else None
            
            # Calculate file hash before operation
            source_hash = self._calculate_file_hash(source_path) if source_path.exists() else None
            
            # Get file metadata
            file_metadata = self._get_file_metadata(source_path) if source_path.exists() else {}
            
            migration_record = {
                'timestamp': datetime.now().isoformat(),
                'transaction_id': self.current_transaction['id'] if self.current_transaction else None,
                'operation': operation,
                'source_path': str(source_path),
                'dest_path': str(dest_path) if dest_path else None,
                'source_hash': source_hash,
                'file_size': file_metadata.get('size', 0),
                'file_modified': file_metadata.get('modified'),
                'file_permissions': file_metadata.get('permissions'),
                'reason': reason,
                'metadata': metadata or {},
                'status': 'pending'
            }
            
            # Add to current transaction if active
            if self.current_transaction:
                self.current_transaction['operations'].append(migration_record)
                self._save_transaction()
            
            # Add to main migration log
            self.migrations.append(migration_record)
            self._save_migrations()
            
            logger.info(f"Tracked migration: {operation} {source_path} -> {dest_path}")
            return migration_record
            
        except Exception as e:
            logger.error(f"Failed to track migration: {e}", exc_info=True)
            raise
    
    def complete_migration(self, migration_record: Dict, success: bool, error: Optional[str] = None):
        """Mark a migration as complete"""
        migration_record['status'] = 'success' if success else 'failed'
        migration_record['completed_at'] = datetime.now().isoformat()
        
        if error:
            migration_record['error'] = error
        
        # If destination exists, calculate its hash
        if success and migration_record.get('dest_path'):
            dest_path = Path(migration_record['dest_path'])
            if dest_path.exists():
                migration_record['dest_hash'] = self._calculate_file_hash(dest_path)
                
                # Verify hashes match for move/copy operations
                if migration_record.get('source_hash') and \
                   migration_record['operation'] in ['move', 'copy', 'archive']:
                    if migration_record['source_hash'] != migration_record['dest_hash']:
                        logger.error(f"Hash mismatch after migration: {migration_record['source_path']}")
                        migration_record['status'] = 'failed'
                        migration_record['error'] = 'Hash verification failed'
        
        self._save_migrations()
        self._save_transaction()
        
        status_emoji = "[OK]" if success else "[FAIL]"
        logger.info(f"{status_emoji} Migration {migration_record['operation']}: "
                   f"{migration_record['source_path']} - {migration_record['status']}")
    
    def commit_transaction(self):
        """Commit the current transaction"""
        if not self.current_transaction:
            logger.warning("No active transaction to commit")
            return
        
        self.current_transaction['end_time'] = datetime.now().isoformat()
        self.current_transaction['status'] = 'committed'
        
        # Check if all operations succeeded
        failed_ops = [op for op in self.current_transaction['operations'] 
                     if op.get('status') != 'success']
        
        if failed_ops:
            self.current_transaction['status'] = 'partial_failure'
            self.current_transaction['failed_operations'] = len(failed_ops)
        
        self._save_transaction()
        self._archive_transaction()
        
        logger.info(f"Committed transaction: {self.current_transaction['id']} "
                   f"- Status: {self.current_transaction['status']}")
        
        self.current_transaction = None
    
    def rollback_transaction(self, transaction_id: Optional[str] = None):
        """Rollback a transaction"""
        if transaction_id:
            # Load specific transaction
            transaction = self._load_transaction(transaction_id)
        else:
            # Use current transaction
            transaction = self.current_transaction
        
        if not transaction:
            logger.error("No transaction to rollback")
            return False
        
        logger.info(f"Rolling back transaction: {transaction['id']}")
        
        # Reverse operations in reverse order
        for operation in reversed(transaction['operations']):
            if operation.get('status') == 'success':
                try:
                    self._reverse_operation(operation)
                    operation['status'] = 'rolled_back'
                    operation['rollback_time'] = datetime.now().isoformat()
                except Exception as e:
                    logger.error(f"Failed to rollback operation: {e}", exc_info=True)
                    operation['rollback_error'] = str(e)
        
        transaction['status'] = 'rolled_back'
        transaction['rollback_time'] = datetime.now().isoformat()
        
        self._save_transaction()
        self._save_migrations()
        
        logger.info(f"Completed rollback of transaction: {transaction['id']}")
        return True
    
    def _reverse_operation(self, operation: Dict):
        """Reverse a single operation"""
        op_type = operation['operation']
        
        if op_type in ['move', 'archive']:
            # Move file back
            source = Path(operation['dest_path'])
            dest = Path(operation['source_path'])
            
            if source.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(dest))
                logger.info(f"Reversed move: {source} -> {dest}")
                
                # Restore permissions if saved
                if operation.get('file_permissions'):
                    try:
                        os.chmod(dest, operation['file_permissions'])
                    except Exception as e:
                        logger.warning(f"Could not restore permissions: {e}")
        
        elif op_type == 'delete':
            # Cannot reverse a delete unless we archived first
            logger.warning(f"Cannot reverse delete operation for: {operation['source_path']}")
        
        elif op_type == 'copy':
            # Delete the copy
            dest = Path(operation['dest_path'])
            if dest.exists():
                dest.unlink()
                logger.info(f"Reversed copy: removed {dest}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _get_file_metadata(self, file_path: Path) -> Dict:
        """Get file metadata"""
        try:
            stat = file_path.stat()
            return {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'permissions': stat.st_mode,
                'is_symlink': file_path.is_symlink(),
                'is_hardlink': stat.st_nlink > 1 if hasattr(stat, 'st_nlink') else False
            }
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            return {}
    
    def _save_migrations(self):
        """Save migration log to disk"""
        try:
            # Write to temporary file first
            temp_path = self.migration_log_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(self.migrations, f, indent=2)
            
            # Atomic replace
            temp_path.replace(self.migration_log_path)
            
        except Exception as e:
            logger.error(f"Failed to save migrations: {e}", exc_info=True)
            raise
    
    def _save_transaction(self):
        """Save current transaction to disk"""
        if not self.current_transaction:
            return
        
        try:
            with open(self.transaction_log_path, 'w') as f:
                json.dump(self.current_transaction, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save transaction: {e}", exc_info=True)
    
    def _archive_transaction(self):
        """Archive completed transaction"""
        if not self.current_transaction:
            return
        
        archive_dir = self.work_dir / 'transactions'
        archive_dir.mkdir(exist_ok=True)
        
        archive_path = archive_dir / f"{self.current_transaction['id']}.json"
        with open(archive_path, 'w') as f:
            json.dump(self.current_transaction, f, indent=2)
    
    def _load_transaction(self, transaction_id: str) -> Optional[Dict]:
        """Load a specific transaction"""
        archive_path = self.work_dir / 'transactions' / f"{transaction_id}.json"
        if archive_path.exists():
            with open(archive_path, 'r') as f:
                return json.load(f)
        return None
    
    def get_migration_summary(self) -> Dict:
        """Get summary of all migrations"""
        summary = {
            'total_migrations': len(self.migrations),
            'successful': len([m for m in self.migrations if m.get('status') == 'success']),
            'failed': len([m for m in self.migrations if m.get('status') == 'failed']),
            'pending': len([m for m in self.migrations if m.get('status') == 'pending']),
            'by_operation': {},
            'total_size_moved': 0
        }
        
        for migration in self.migrations:
            op = migration['operation']
            if op not in summary['by_operation']:
                summary['by_operation'][op] = 0
            summary['by_operation'][op] += 1
            
            if migration.get('status') == 'success' and migration.get('file_size'):
                summary['total_size_moved'] += migration['file_size']
        
        return summary
    
    def verify_migration_integrity(self) -> List[Dict]:
        """Verify integrity of all successful migrations"""
        issues = []
        
        for migration in self.migrations:
            if migration.get('status') != 'success':
                continue
            
            # Check if destination still exists and matches hash
            if migration.get('dest_path') and migration.get('dest_hash'):
                dest_path = Path(migration['dest_path'])
                if not dest_path.exists():
                    issues.append({
                        'type': 'missing_destination',
                        'migration': migration,
                        'message': f"Destination file missing: {dest_path}"
                    })
                else:
                    current_hash = self._calculate_file_hash(dest_path)
                    if current_hash != migration['dest_hash']:
                        issues.append({
                            'type': 'hash_mismatch',
                            'migration': migration,
                            'message': f"File hash changed: {dest_path}",
                            'expected_hash': migration['dest_hash'],
                            'current_hash': current_hash
                        })
            
            # Check if source was properly removed for move operations
            if migration['operation'] == 'move' and migration.get('source_path'):
                source_path = Path(migration['source_path'])
                if source_path.exists():
                    issues.append({
                        'type': 'source_not_removed',
                        'migration': migration,
                        'message': f"Source file still exists after move: {source_path}"
                    })
        
        return issues
