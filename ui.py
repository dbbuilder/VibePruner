"""
Interactive UI for VibePruner using Rich library
"""

import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.layout import Layout
from rich.live import Live
import json


class InteractiveUI:
    """Terminal-based interactive UI using Rich"""
    
    def __init__(self, config):
        self.config = config
        self.console = Console()
    
    def review_proposals(self, proposals, file_analysis):
        """Interactive review of proposed actions"""
        self.console.clear()
        self.console.print("[bold blue]VibePruner - File Cleanup Review[/bold blue]\n")
        
        # Group proposals by action
        grouped = self._group_proposals(proposals)
        
        # Show summary
        self._show_summary(grouped, file_analysis)
        
        # Review each group
        approved_actions = []
        
        for action_type, action_proposals in grouped.items():
            if not action_proposals:
                continue
            
            self.console.print(f"\n[bold yellow]Reviewing {action_type.upper()} actions ({len(action_proposals)} files)[/bold yellow]")
            
            # Bulk approval option
            if len(action_proposals) > 5:
                if Confirm.ask(f"Review all {action_type} actions individually?", default=False):
                    approved = self._review_individual(action_proposals, file_analysis)
                    approved_actions.extend(approved)
                else:
                    # Show summary and ask for bulk approval
                    self._show_action_summary(action_proposals)
                    if Confirm.ask(f"Approve all {action_type} actions?", default=True):
                        approved_actions.extend(action_proposals)
            else:
                # Review individually for small sets
                approved = self._review_individual(action_proposals, file_analysis)
                approved_actions.extend(approved)
        
        # Final confirmation
        if approved_actions:
            self.console.print(f"\n[bold green]Total approved actions: {len(approved_actions)}[/bold green]")
            if not Confirm.ask("Proceed with approved actions?", default=True):
                return []
        
        return approved_actions
    
    def _group_proposals(self, proposals):
        """Group proposals by action type"""
        grouped = {
            'delete': [],
            'archive': [],
            'consolidate': []
        }
        
        for proposal in proposals:
            action = proposal.get('action', 'archive')
            if action in grouped:
                grouped[action].append(proposal)
        
        return grouped
    
    def _show_summary(self, grouped, file_analysis):
        """Show summary of analysis and proposals"""
        table = Table(title="Analysis Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Total Files", str(file_analysis['total_files']))
        table.add_row("Orphaned Files", str(len(file_analysis.get('orphaned_files', []))))
        table.add_row("Proposed Deletions", str(len(grouped['delete'])))
        table.add_row("Proposed Archives", str(len(grouped['archive'])))
        
        # Calculate space savings
        total_size = 0
        for action_list in grouped.values():
            for action in action_list:
                file_path = action['file_path']
                if file_path in file_analysis['files']:
                    total_size += file_analysis['files'][file_path].get('size', 0)
        
        table.add_row("Potential Space Savings", self._format_size(total_size))
        
        self.console.print(table)
    
    def _show_action_summary(self, proposals):
        """Show summary of proposed actions"""
        table = Table(title="Proposed Actions")
        table.add_column("File", style="cyan", width=50)
        table.add_column("Reason", style="yellow")
        table.add_column("Confidence", style="magenta")
        
        # Show first 10 and count
        for i, proposal in enumerate(proposals[:10]):
            confidence = proposal.get('confidence', 0.5)
            conf_str = f"{confidence:.0%}"
            if confidence > 0.7:
                conf_str = f"[green]{conf_str}[/green]"
            elif confidence < 0.5:
                conf_str = f"[red]{conf_str}[/red]"
            
            table.add_row(
                self._truncate_path(proposal['file_path'], 50),
                proposal.get('reason', 'Unknown'),
                conf_str
            )
        
        if len(proposals) > 10:
            table.add_row("...", f"... and {len(proposals) - 10} more files", "...")
        
        self.console.print(table)
    
    def _review_individual(self, proposals, file_analysis):
        """Review proposals individually"""
        approved = []
        
        for i, proposal in enumerate(proposals):
            self.console.clear()
            self.console.print(f"[bold]Reviewing {i+1} of {len(proposals)}[/bold]\n")
            
            # Show file details
            self._show_file_details(proposal, file_analysis)
            
            # Show file preview if small enough
            file_path = Path(proposal['file_path'])
            if file_path.exists() and file_path.stat().st_size < 10000:  # 10KB
                self._show_file_preview(file_path)
            
            # Ask for approval
            if Confirm.ask(f"Approve {proposal['action']} for this file?", default=True):
                # Option to add reason
                if Confirm.ask("Add a reason/comment?", default=False):
                    reason = Prompt.ask("Reason")
                    proposal['user_reason'] = reason
                
                approved.append(proposal)
            
            # Option to stop reviewing
            if i < len(proposals) - 1:
                if not Confirm.ask("Continue reviewing?", default=True):
                    remaining = proposals[i+1:]
                    if Confirm.ask(f"Approve all remaining {len(remaining)} files?", default=False):
                        approved.extend(remaining)
                    break
        
        return approved
    
    def _show_file_details(self, proposal, file_analysis):
        """Show detailed information about a file"""
        file_path = proposal['file_path']
        file_info = file_analysis['files'].get(file_path, {})
        
        # Create details panel
        details = f"""[bold]File:[/bold] {file_path}
[bold]Action:[/bold] {proposal['action'].upper()}
[bold]Reason:[/bold] {proposal.get('reason', 'Unknown')}
[bold]Confidence:[/bold] {proposal.get('confidence', 0.5):.0%}

[bold]File Details:[/bold]
  Size: {self._format_size(file_info.get('size', 0))}
  Modified: {file_info.get('days_since_modified', 0)} days ago
  Type: {file_info.get('extension', 'Unknown')}
  References: {file_info.get('reference_count', 0)}
  Is Test: {'Yes' if file_info.get('is_test') else 'No'}
  Is Temp: {'Yes' if file_info.get('is_temp') else 'No'}"""
        
        panel = Panel(details, title="File Information", border_style="blue")
        self.console.print(panel)
    
    def _show_file_preview(self, file_path):
        """Show preview of file contents"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(500)  # First 500 chars
                if len(content) < f.seek(0, 2):  # Check if truncated
                    content += "\n... (truncated)"
            
            # Determine syntax highlighting
            lexer = self._get_lexer(file_path.suffix)
            syntax = Syntax(content, lexer, theme="monokai", line_numbers=True)
            
            panel = Panel(syntax, title="File Preview", border_style="green")
            self.console.print(panel)
            
        except Exception as e:
            self.console.print(f"[red]Could not preview file: {e}[/red]")
    
    def _get_lexer(self, extension):
        """Get syntax highlighting lexer for file extension"""
        lexer_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.cs': 'csharp',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.sql': 'sql',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.md': 'markdown',
            '.sh': 'bash',
            '.ps1': 'powershell'
        }
        
        return lexer_map.get(extension.lower(), 'text')
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _truncate_path(self, path, max_len):
        """Truncate long paths for display"""
        if len(path) <= max_len:
            return path
        
        parts = path.split('/')
        if len(parts) <= 2:
            return path[:max_len-3] + "..."
        
        # Keep first and last parts
        start = parts[0]
        end = parts[-1]
        middle = "..."
        
        while len(f"{start}/{middle}/{end}") > max_len and len(parts) > 2:
            parts = parts[1:-1]
            if parts:
                middle = f".../{parts[-1]}"
        
        return f"{start}/{middle}/{end}"
    
    def show_progress(self, message, total=None):
        """Show progress indicator"""
        if total:
            return Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            )
        else:
            with self.console.status(message):
                pass
    
    def show_error(self, message):
        """Show error message"""
        self.console.print(f"[bold red]Error:[/bold red] {message}")
    
    def show_success(self, message):
        """Show success message"""
        self.console.print(f"[bold green]Success:[/bold green] {message}")
    
    def show_warning(self, message):
        """Show warning message"""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
