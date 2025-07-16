#!/usr/bin/env python3
"""
VibePruner - Intelligent file cleanup with test protection
Main entry point for the application with enhanced reliability
"""

import os
import sys
import json
import argparse
import logging
import traceback
from pathlib import Path
from datetime import datetime

from analyzer import FileAnalyzer
from test_guardian import TestGuardian
from md_parser import MarkdownParser
from project_parser import ProjectParser
from ui import InteractiveUI
from config import Config
from migration_tracker import MigrationTracker
from rollback_manager import RollbackManager
from session_manager import SessionManager
from audit_logger import AuditLogger, AuditEvent

# Set up logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vibepruner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VibePruner:
    """Main application class with enhanced error handling and tracking"""
    
    def __init__(self, project_path: str, config_path: str = None):
        self.project_path = Path(project_path).resolve()
        self.config = Config(config_path)
        self.work_dir = self.project_path / '.vibepruner'
        self.work_dir.mkdir(exist_ok=True)
        
        # Initialize core components
        self.analyzer = FileAnalyzer(self.config)
        self.test_guardian = TestGuardian(self.config)
        self.md_parser = MarkdownParser(self.config)
        self.project_parser = ProjectParser(self.config)
        self.ui = InteractiveUI(self.config)
        
        # Initialize tracking components
        self.migration_tracker = MigrationTracker(self.work_dir)
        self.rollback_manager = RollbackManager(self.migration_tracker, self.work_dir)
        self.session_manager = SessionManager(self.work_dir)
        self.audit_logger = AuditLogger(self.work_dir)
        
        # Register shutdown handlers
        self.session_manager.register_shutdown_handler(self._emergency_save)
        
    def run(self, resume_session: str = None, dry_run: bool = False):
        """Main execution flow with comprehensive error handling"""
        try:
            # Start or resume session
            session = self.session_manager.start_session(
                str(self.project_path), 
                resume_session
            )
            
            self.audit_logger.log_event(
                AuditEvent.SESSION_START,
                f"Started VibePruner session for {self.project_path}",
                {'session_id': session['id'], 'resumed': bool(resume_session)}
            )
            
            logger.info(f"Starting VibePruner analysis for: {self.project_path}")
            
            # Create rollback point
            rollback_id = self.rollback_manager.create_rollback_point(
                f"Pre-analysis state for {self.project_path.name}"
            )
            
            # Step 1: Discover and run tests to establish baseline
            if not self._establish_test_baseline():
                return False
            
            # Step 2: Analyze file structure
            file_analysis = self._analyze_files()
            if not file_analysis:
                return False
            
            # Step 3: Parse project files for dependencies
            project_deps = self._parse_project_dependencies()
            
            # Step 4: Analyze markdown references
            md_refs = self._analyze_markdown_references()
            
            # Step 5: Generate proposals
            proposals = self._generate_proposals(
                file_analysis, project_deps, md_refs
            )
            
            if not proposals:
                print("\n[OK] No cleanup actions needed. Your project is already clean!")
                self.session_manager.end_session('completed')
                return True
            
            # Step 6: Interactive review
            approved_actions = self._review_proposals(proposals, file_analysis)
            
            if not approved_actions:
                print("\n[FAIL] No actions approved. Exiting.")
                self.session_manager.end_session('cancelled')
                return True
            
            if dry_run:
                print("\n[SEARCH] Dry run mode - no actual changes will be made.")
                self._show_dry_run_summary(approved_actions)
                self.session_manager.end_session('dry_run')
                return True
            
            # Step 7: Execute approved actions
            execution_results = self._execute_actions(approved_actions)
            
            # Step 8: Validate tests still work
            validation_success = self._validate_tests()
            
            if not validation_success:
                print("\n[FAIL] Test validation failed! Rolling back changes...")
                self._perform_rollback(rollback_id)
                return False
            
            print("\n[OK] All tests passed! Changes are safe.")
            
            # Step 9: Complete session
            self._complete_session(approved_actions, execution_results)
            
            print("\n[DONE] VibePruner completed successfully!")
            return True
            
        except KeyboardInterrupt:
            logger.info("User interrupted execution")
            self._handle_interruption()
            return False
            
        except Exception as e:
            logger.error(f"Fatal error during execution: {e}", exc_info=True)
            self.audit_logger.log_error(
                str(e),
                type(e).__name__,
                traceback.format_exc(),
                {'phase': self.session_manager.session.get('phase') if self.session_manager.session else 'unknown'}
            )
            print(f"\n[FAIL] Fatal error: {e}")
            self._handle_fatal_error(e)
            return False
    
    def _establish_test_baseline(self) -> bool:
        """Establish test baseline with error handling"""
        print("\nDiscovering and running tests...")
        self.session_manager.update_phase('test_baseline')
        
        try:
            test_baseline = self.test_guardian.create_baseline(self.project_path)
            
            if not test_baseline['success']:
                print("[FAIL] Failed to establish test baseline.")
                response = input("Continue without test protection? (y/N): ")
                if response.lower() != 'y':
                    return False
                test_baseline = {'tests': [], 'success': True}
            
            self._save_json('test_baseline.json', test_baseline)
            self.session_manager.add_checkpoint('test_baseline', test_baseline)
            
            print(f"[OK] Found {len(test_baseline['tests'])} test suites")
            
            # Log test results
            for test in test_baseline['tests']:
                self.audit_logger.log_test_result(
                    test['command'],
                    'success' if test['exit_code'] == 0 else 'failed',
                    test.get('duration', 0)
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error establishing test baseline: {e}", exc_info=True)
            self.session_manager.record_error(str(e), {'phase': 'test_baseline'})
            return False
    
    def _analyze_files(self) -> dict:
        """Analyze files with progress tracking"""
        print("\n[DIR] Analyzing file structure...")
        self.session_manager.update_phase('file_analysis')
        
        try:
            file_analysis = self.analyzer.analyze_directory(self.project_path)
            
            self.session_manager.update_stats(
                files_analyzed=file_analysis['total_files']
            )
            
            self.audit_logger.log_event(
                AuditEvent.FILE_SCAN,
                f"Completed file analysis: {file_analysis['total_files']} files",
                {'file_types': file_analysis['file_types']}
            )
            
            print(f"[OK] Analyzed {file_analysis['total_files']} files")
            return file_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing files: {e}", exc_info=True)
            self.session_manager.record_error(str(e), {'phase': 'file_analysis'})
            return {}
    
    def _parse_project_dependencies(self) -> dict:
        """Parse project dependencies with error handling"""
        print("\n[LINK] Parsing project dependencies...")
        self.session_manager.update_phase('dependency_parsing')
        
        try:
            project_deps = self.project_parser.parse_project(self.project_path)
            
            self.session_manager.add_checkpoint('project_deps', project_deps)
            
            print(f"[OK] Found {len(project_deps['required_files'])} required files")
            return project_deps
            
        except Exception as e:
            logger.error(f"Error parsing project dependencies: {e}", exc_info=True)
            self.session_manager.record_error(str(e), {'phase': 'dependency_parsing'})
            return {'required_files': [], 'entry_points': [], 'build_files': []}
    
    def _analyze_markdown_references(self) -> dict:
        """Analyze markdown references with error handling"""
        print("\n[DOC] Analyzing documentation references...")
        self.session_manager.update_phase('markdown_analysis')
        
        try:
            md_refs = self.md_parser.analyze_markdown_files(self.project_path)
            
            self.session_manager.add_checkpoint('markdown_refs', md_refs)
            
            print(f"[OK] Analyzed {len(md_refs['markdown_files'])} documentation files")
            return md_refs
            
        except Exception as e:
            logger.error(f"Error analyzing markdown files: {e}", exc_info=True)
            self.session_manager.record_error(str(e), {'phase': 'markdown_analysis'})
            return {'markdown_files': [], 'referenced_files': [], 'required_files': [], 'temporary_files': []}
    
    def _generate_proposals(self, file_analysis, project_deps, md_refs):
        """Generate action proposals with comprehensive tracking"""
        print("\n[THINK] Generating cleanup proposals...")
        self.session_manager.update_phase('proposal_generation')
        
        proposals = []
        test_baseline = self._load_json('test_baseline.json')
        
        for file_path, file_info in file_analysis['files'].items():
            try:
                # Skip if file is required by project
                if file_path in project_deps['required_files']:
                    continue
                    
                # Skip if file is protected by config
                if any(pattern in file_path for pattern in self.config.protected_patterns):
                    continue
                
                # Calculate confidence score
                score = self._calculate_confidence_score(
                    file_path, file_info, project_deps, md_refs, test_baseline
                )
                
                # Generate proposal based on score and characteristics
                proposal = self._create_proposal(file_path, file_info, score)
                if proposal:
                    proposals.append(proposal)
                    
                    self.audit_logger.log_event(
                        AuditEvent.PROPOSAL_GENERATE,
                        f"Generated {proposal['action']} proposal for {file_path}",
                        {'confidence': score, 'reason': proposal['reason']}
                    )
            
            except Exception as e:
                logger.error(f"Error generating proposal for {file_path}: {e}")
                continue
        
        self.session_manager.add_checkpoint('proposals', proposals)
        print(f"[OK] Generated {len(proposals)} proposals")
        
        return proposals
    
    def _review_proposals(self, proposals, file_analysis):
        """Review proposals with decision tracking"""
        print("\n[REVIEW] Starting interactive review...")
        self.session_manager.update_phase('user_review')
        
        approved_actions = self.ui.review_proposals(proposals, file_analysis)
        
        # Log all user decisions
        for proposal in proposals:
            approved = proposal in approved_actions
            self.audit_logger.log_user_decision(
                proposal['file_path'],
                proposal['action'],
                'approved' if approved else 'rejected',
                proposal.get('user_reason'),
                proposal.get('confidence')
            )
        
        self.session_manager.add_checkpoint('approved_actions', approved_actions)
        
        return approved_actions
    
    def _execute_actions(self, approved_actions):
        """Execute approved actions with transaction tracking"""
        print(f"\n[RUN] Executing {len(approved_actions)} approved actions...")
        self.session_manager.update_phase('execution')
        
        # Start migration transaction
        transaction_id = self.migration_tracker.start_transaction(
            f"VibePruner cleanup - {len(approved_actions)} actions"
        )
        
        results = []
        archive_dir = self.project_path / '.vibepruner_archive' / datetime.now().strftime('%Y%m%d_%H%M%S')
        
        with self.ui.show_progress("Executing actions", len(approved_actions)) as progress:
            task = progress.add_task("Processing files", total=len(approved_actions))
            
            for i, action in enumerate(approved_actions):
                try:
                    # Track migration
                    migration_record = self.migration_tracker.track_migration(
                        Path(action['file_path']),
                        archive_dir / Path(action['file_path']).relative_to(self.project_path),
                        action['action'],
                        action['reason'],
                        {'confidence': action.get('confidence')}
                    )
                    
                    # Execute action
                    result = self._execute_single_action(action, archive_dir)
                    results.append(result)
                    
                    # Complete migration tracking
                    self.migration_tracker.complete_migration(
                        migration_record,
                        result['success'],
                        result.get('error')
                    )
                    
                    # Update session
                    self.session_manager.record_operation(result)
                    
                    progress.update(task, advance=1)
                    
                except Exception as e:
                    logger.error(f"Error executing action on {action['file_path']}: {e}")
                    results.append({
                        'file_path': action['file_path'],
                        'action': action['action'],
                        'success': False,
                        'error': str(e)
                    })
        
        # Commit transaction
        self.migration_tracker.commit_transaction()
        
        return results
    
    def _execute_single_action(self, action, archive_dir):
        """Execute a single action with error handling"""
        source = Path(action['file_path'])
        
        if action['action'] == 'delete':
            # Never actually delete - always archive
            action['action'] = 'archive'
        
        if action['action'] == 'archive':
            if source.exists():
                relative = source.relative_to(self.project_path)
                target = archive_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # Log the operation
                self.audit_logger.log_file_operation(
                    'archive',
                    source,
                    target,
                    metadata={'reason': action['reason']}
                )
                
                source.rename(target)
                
                return {
                    'file_path': str(source),
                    'action': 'archived',
                    'target_path': str(target),
                    'success': True
                }
        
        return {
            'file_path': action['file_path'],
            'action': action['action'],
            'success': False,
            'error': f"Unknown action: {action['action']}"
        }
    
    def _validate_tests(self) -> bool:
        """Validate tests with comprehensive comparison"""
        print("\n[TEST] Validating tests after changes...")
        self.session_manager.update_phase('test_validation')
        
        try:
            test_baseline = self._load_json('test_baseline.json')
            validation_result = self.test_guardian.validate_against_baseline(
                self.project_path, test_baseline
            )
            
            # Log validation results
            for comparison in validation_result.get('comparison_details', []):
                self.audit_logger.log_test_result(
                    comparison.get('command', 'unknown'),
                    'passed' if comparison.get('matches') else 'failed',
                    0,
                    comparison
                )
            
            self.session_manager.add_checkpoint('test_validation', validation_result)
            
            return validation_result['success']
            
        except Exception as e:
            logger.error(f"Error validating tests: {e}", exc_info=True)
            self.session_manager.record_error(str(e), {'phase': 'test_validation'})
            return False
    
    def _perform_rollback(self, rollback_id):
        """Perform rollback with verification"""
        self.session_manager.update_phase('rollback')
        
        self.audit_logger.log_event(
            AuditEvent.ROLLBACK,
            f"Starting rollback to point: {rollback_id}",
            {'reason': 'test_validation_failed'}
        )
        
        success, errors = self.rollback_manager.rollback_to_point(rollback_id)
        
        if success:
            print("[OK] Rollback completed successfully")
        else:
            print(f"[WARN]  Rollback completed with {len(errors)} errors")
            for error in errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        self.session_manager.end_session('rolled_back')
    
    def _complete_session(self, approved_actions, execution_results):
        """Complete session with summary"""
        self.session_manager.update_phase('completion')
        
        # Generate summary
        summary = {
            'total_actions': len(approved_actions),
            'successful': len([r for r in execution_results if r.get('success')]),
            'failed': len([r for r in execution_results if not r.get('success')]),
            'space_freed': sum(
                Path(r['file_path']).stat().st_size 
                for r in execution_results 
                if r.get('success') and Path(r['file_path']).exists()
            )
        }
        
        self.session_manager.add_checkpoint('summary', summary)
        
        # Show summary
        print(f"\n[STATS] Summary:")
        print(f"  - Actions executed: {summary['successful']}/{summary['total_actions']}")
        print(f"  - Space freed: {self._format_size(summary['space_freed'])}")
        
        # End session
        self.session_manager.end_session('completed')
        
        # Final audit log
        self.audit_logger.log_event(
            AuditEvent.SESSION_END,
            "VibePruner session completed successfully",
            summary
        )
    
    def _show_dry_run_summary(self, approved_actions):
        """Show summary for dry run"""
        total_size = 0
        by_action = {}
        
        for action in approved_actions:
            action_type = action['action']
            if action_type not in by_action:
                by_action[action_type] = []
            by_action[action_type].append(action['file_path'])
            
            try:
                total_size += Path(action['file_path']).stat().st_size
            except:
                pass
        
        print(f"\n[STATS] Dry Run Summary:")
        print(f"  Total files to process: {len(approved_actions)}")
        print(f"  Estimated space to free: {self._format_size(total_size)}")
        
        for action_type, files in by_action.items():
            print(f"\n  {action_type.upper()} ({len(files)} files):")
            for file in files[:5]:  # Show first 5
                print(f"    - {file}")
            if len(files) > 5:
                print(f"    ... and {len(files) - 5} more")
    
    def _handle_interruption(self):
        """Handle user interruption gracefully"""
        print("\n\n[WARN]  Execution interrupted by user")
        print("Session state has been saved.")
        
        session_id = self.session_manager.session['id'] if self.session_manager.session else 'unknown'
        print(f"\nTo resume this session, run:")
        print(f"  python vibepruner.py {self.project_path} --resume {session_id}")
        
        self.session_manager.end_session('interrupted')
    
    def _handle_fatal_error(self, error):
        """Handle fatal errors with recovery information"""
        print("\n[SAVE] Emergency save completed.")
        print("Session data has been preserved.")
        
        if self.session_manager.session:
            session_id = self.session_manager.session['id']
            print(f"\nTo attempt recovery, run:")
            print(f"  python vibepruner.py {self.project_path} --resume {session_id}")
        
        print("\nFor support, check the log file: vibepruner.log")
        
        self.session_manager.end_session('failed')
    
    def _emergency_save(self):
        """Emergency save function for shutdown handler"""
        try:
            if self.session_manager.session:
                self.session_manager.session['emergency_save'] = True
                self.session_manager._save_session()
                logger.info("Emergency save completed")
        except Exception as e:
            logger.error(f"Emergency save failed: {e}")
    
    def _calculate_confidence_score(self, file_path, file_info, project_deps, md_refs, test_baseline):
        """Calculate confidence score for action proposal"""
        score = 0.5  # Base score
        
        # Orphaned file (no incoming references)
        if file_info.get('reference_count', 0) == 0:
            score += 0.2
        
        # Not mentioned in documentation
        if file_path not in md_refs.get('referenced_files', []):
            score += 0.1
        else:
            score -= 0.2  # Mentioned in docs, probably important
        
        # Marked as temporary in docs
        if file_path in md_refs.get('temporary_files', []):
            score += 0.3
        
        # Not in test files
        if not any(test['file_path'] == file_path for test in test_baseline.get('tests', [])):
            score += 0.1
        
        # File patterns
        if any(pattern in file_path.lower() for pattern in ['temp', 'tmp', 'backup', 'old']):
            score += 0.2
        
        # Age and size factors
        if file_info.get('days_since_modified', 0) > 180:
            score += 0.1
        
        return min(max(score, 0.0), 1.0)  # Clamp between 0 and 1
    
    def _create_proposal(self, file_path, file_info, score):
        """Create action proposal for a file"""
        # High confidence for removal
        if score > 0.7:
            if any(pattern in file_path.lower() for pattern in ['log', 'tmp', 'temp']):
                return {
                    'file_path': file_path,
                    'action': 'delete',
                    'reason': 'Temporary/log file with no references',
                    'confidence': score
                }
            else:
                return {
                    'file_path': file_path,
                    'action': 'archive',
                    'reason': 'Unreferenced file, safe to archive',
                    'confidence': score
                }
        
        # Medium confidence
        elif score > 0.5:
            return {
                'file_path': file_path,
                'action': 'archive',
                'reason': 'Possibly unused, recommend archiving',
                'confidence': score
            }
        
        return None
    
    def _save_json(self, filename, data):
        """Save data to JSON file in work directory"""
        file_path = self.work_dir / filename
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_json(self, filename):
        """Load data from JSON file in work directory"""
        file_path = self.work_dir / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


def main():
    """Main entry point with enhanced argument parsing"""
    parser = argparse.ArgumentParser(
        description='VibePruner - Intelligent file cleanup with test protection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/project              # Analyze and clean project
  %(prog)s /path/to/project --dry-run    # Preview changes without executing
  %(prog)s /path/to/project --resume abc123  # Resume interrupted session
  %(prog)s /path/to/project --audit-report   # Generate audit report
        """
    )
    
    parser.add_argument('path', help='Path to the project directory')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--dry-run', action='store_true', help='Show proposals without executing')
    parser.add_argument('--resume', help='Resume a previous session by ID')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--audit-report', action='store_true', help='Generate audit report')
    parser.add_argument('--export-audit', help='Export audit log to file')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    # Validate project path
    project_path = Path(args.path)
    if not project_path.exists():
        print(f"[FAIL] Error: Project path does not exist: {project_path}")
        sys.exit(1)
    
    if not project_path.is_dir():
        print(f"[FAIL] Error: Project path is not a directory: {project_path}")
        sys.exit(1)
    
    # Handle special commands
    if args.audit_report or args.export_audit:
        pruner = VibePruner(str(project_path), args.config)
        
        if args.audit_report:
            report = pruner.audit_logger.generate_audit_report()
            print(json.dumps(report, indent=2))
        
        if args.export_audit:
            output_path = Path(args.export_audit)
            export_format = 'csv' if output_path.suffix == '.csv' else 'json'
            pruner.audit_logger.export_audit_log(output_path, export_format)
            print(f"[OK] Audit log exported to: {output_path}")
        
        sys.exit(0)
    
    # Run VibePruner
    pruner = VibePruner(str(project_path), args.config)
    success = pruner.run(resume_session=args.resume, dry_run=args.dry_run)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
