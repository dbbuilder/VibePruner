# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VibePruner is an intelligent file analysis and cleanup tool built with .NET 8.0. It uses AI to:
- Identify unreferenced/orphaned files in codebases
- Archive unnecessary files while maintaining folder structure
- Consolidate documentation using AI providers (Claude, OpenAI, Gemini)
- Clean up logs, exports, and temporary files
- Protect core project files from deletion

## Build and Development Commands

### Essential Commands
```bash
# Restore NuGet packages
dotnet restore

# Build the entire solution
dotnet build

# Build in Release mode
dotnet build --configuration Release

# Run tests
dotnet test

# Run tests with detailed output
dotnet test --logger "console;verbosity=detailed"

# Run the CLI application (from src/VibePruner.CLI directory)
dotnet run

# Run the API (from src/VibePruner.API directory)
dotnet run
```

### CLI Usage Commands
```bash
# Analyze a folder
vibepruner analyze "C:\MyProject"

# Archive unreferenced files (with dry run)
vibepruner archive "C:\MyProject" --dry-run

# Consolidate documentation
vibepruner consolidate "C:\MyProject" --ai-provider claude

# Clean up logs and temporary files older than 30 days
vibepruner clean "C:\MyProject" --older-than 30

# Generate comprehensive report
vibepruner report "C:\MyProject"
```

## Architecture Overview

The solution follows Clean Architecture principles with clear separation of concerns:

- **VibePruner.Core**: Domain models, interfaces, and business rules
- **VibePruner.Infrastructure**: Data access (Entity Framework Core), external service implementations, AI provider integrations
- **VibePruner.Application**: Command handlers, orchestration logic, and use cases
- **VibePruner.API**: RESTful API endpoints for web integration
- **VibePruner.CLI**: Command-line interface for direct usage

### Key Technologies
- **.NET 8.0** (for Azure Linux App Service compatibility)
- **Entity Framework Core** with SQL Server
- **Serilog** for structured logging
- **Polly** for resilience and retry policies
- **Azure Key Vault** for secret management
- **Application Insights** for monitoring
- **AI SDKs**: Anthropic Claude, OpenAI, Google Gemini

## Database Setup

SQL Server database with three main tables:
- `AnalysisSessions`: Tracks analysis runs and their metadata
- `FileItems`: Stores file information including dependencies
- `ProposedFileActions`: Records recommended actions for files

Run these scripts to set up the database:
```bash
# From database/Tables directory
sqlcmd -S <server> -d VibePruner -i 01_CreateTables.sql
sqlcmd -S <server> -d VibePruner -i 02_CreateAdditionalTables.sql
```

## Configuration

Key configuration in `appsettings.json`:
- **AI Providers**: Configure API keys and endpoints for Claude, OpenAI, and Gemini
- **Archive Settings**: Compression levels, retention periods, archive paths
- **Protected Files**: Patterns for files that should never be deleted (e.g., `.git/**/*`, `*.csproj`)
- **Connection Strings**: Database connection for VibePruner database
- **Azure Integration**: Key Vault URI and Application Insights connection

## Development Notes

### Current Project State
- Project is in early development (Stage 1.1 of TODO.md)
- Core project structure is created but implementation is pending
- Solution file exists but projects need to be added to it
- Run `scripts/setup.ps1` from Windows PowerShell to create project structure

### Important Patterns
- Use dependency injection for all services
- Implement repository pattern for data access
- Use command/query pattern for operations
- Apply resilience patterns (Polly) for external service calls
- Structure logging with Serilog for better observability

### AI Integration Guidelines
- Each AI provider has specific token limits configured
- Use the appropriate provider based on task complexity
- Implement fallback patterns between providers
- Log AI usage for cost tracking

### File Analysis Engine
- Respect protected file patterns from configuration
- Track file dependencies to avoid breaking references
- Support multiple programming languages and frameworks
- Generate detailed reports before any destructive operations

## Testing Strategy

When implementing tests:
- Unit tests for Core domain logic
- Integration tests for Infrastructure components
- Use test databases for Entity Framework tests
- Mock AI providers for consistent test results
- Test file system operations with temporary directories