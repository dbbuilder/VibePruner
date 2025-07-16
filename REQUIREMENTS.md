# VibePruner Requirements Specification

## Overview
VibePruner is an intelligent file analysis and cleanup tool that uses AI to analyze file structures, identify unreferenced files, consolidate documentation, and clean up unnecessary files while preserving core project assets.

## Core Requirements

### 1. File Analysis Engine
- Analyze all files in a specified folder recursively
- Build a dependency graph of file references
- Identify unreferenced files (orphaned files)
- Support multiple file types: .bat, .sql, .ps1, .cs, .py, .js, .html, etc.

### 2. Archive Management
- Create archive folder structure for unreferenced files
- Maintain original folder hierarchy in archives
- Generate archive manifest with reasons for archival
- Support restore functionality from archives

### 3. Documentation Consolidation
- Use AI (Claude/OpenAI/Gemini) to analyze and consolidate documentation
- Protected files list: README.md, REQUIREMENTS.md, SETUP.md, TODO.md, LICENSE, etc.
- Merge similar documentation files
- Generate consolidated documentation report

### 4. Cleanup Operations
- Remove logs, exports, and reports based on age and patterns
- Identify and handle temp/test files
- Clean up empty directories
- Generate cleanup report with actions taken

### 5. AI Integration
- Token optimization through file preprocessing
- Separate file structure analysis from content analysis
- Support multiple AI providers (Claude, OpenAI, Gemini)
- Configurable AI endpoints and API keys

### 6. Core File Protection
- Preserve all core code files by default
- Identify temp/test files through naming patterns
- Configurable protection rules
- Override mechanism for specific files

### 7. Command Line Interface
- analyze <folder> - Analyze folder structure
- archive <folder> - Archive unreferenced files
- consolidate <folder> - Consolidate documentation
- clean <folder> - Clean logs/exports/reports
- restore <archive> - Restore archived files
- report - Generate analysis report

### 8. Configuration
- JSON-based configuration file
- Protected file patterns
- Archive location settings
- AI provider configuration
- Cleanup rules and thresholds

### 9. Reporting
- Detailed analysis reports
- Dependency visualization
- Archive manifests
- Consolidation summaries
- Cleanup logs

### 10. Safety Features
- Dry-run mode for all operations
- Confirmation prompts for destructive actions
- Backup before major operations
- Rollback capability

## Technical Requirements

### Platform
- .NET Core 8.0 for Azure Linux App Service compatibility
- Cross-platform support (Windows/Linux/Mac)

### Dependencies
- Entity Framework Core for data persistence
- Serilog for logging
- Polly for resilience
- Azure SDK for cloud integration
- AI provider SDKs

### Performance
- Handle large codebases (10,000+ files)
- Token optimization for AI analysis
- Parallel processing where applicable
- Progress reporting for long operations

### Security
- Azure Key Vault integration for API keys
- Secure handling of sensitive files
- Audit trail for all operations

## Success Criteria
1. Accurately identify file dependencies
2. Safely archive unreferenced files
3. Effectively consolidate documentation
4. Clean up unnecessary files without data loss
5. Provide clear, actionable reports
6. Maintain project integrity throughout operations