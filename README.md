# VibePruner

## Overview
VibePruner is an intelligent file analysis and cleanup tool that helps developers maintain clean, organized codebases by identifying unreferenced files, consolidating documentation, and removing unnecessary artifacts.

## Features
- **Dependency Analysis**: Analyzes file references to identify orphaned files
- **Smart Archiving**: Archives unreferenced files while maintaining folder structure
- **Documentation AI**: Uses AI to consolidate and improve documentation
- **Automated Cleanup**: Removes logs, exports, and temporary files
- **Multi-Platform**: Runs on Windows, Linux, and macOS
- **Cloud-Ready**: Designed for Azure deployment

## Installation

### Prerequisites
- .NET 8.0 SDK or later
- Azure subscription (for cloud features)
- AI API keys (Claude, OpenAI, or Gemini)

### Setup Steps
1. Clone the repository
2. Navigate to the project directory
3. Restore NuGet packages: `dotnet restore`
4. Configure appsettings.json with your API keys
5. Build the project: `dotnet build`
6. Run: `dotnet run`

## Usage

### Basic Commands
```bash
# Analyze a folder
vibepruner analyze "C:\MyProject"

# Archive unreferenced files
vibepruner archive "C:\MyProject" --dry-run

# Consolidate documentation
vibepruner consolidate "C:\MyProject" --ai-provider claude

# Clean up logs and temporary files
vibepruner clean "C:\MyProject" --older-than 30

# Generate comprehensive report
vibepruner report "C:\MyProject"
```

### Configuration
Edit `appsettings.json` to customize:
- Protected file patterns
- Archive locations
- AI provider settings
- Cleanup rules

## Architecture
- **Core**: Business logic and domain models
- **Infrastructure**: Data access and external services
- **Application**: Command handlers and orchestration
- **API**: RESTful endpoints for integration
- **CLI**: Command-line interface

## Development
This project uses:
- Entity Framework Core with stored procedures
- Serilog for structured logging
- Polly for resilience patterns
- Azure Key Vault for secrets
- Application Insights for monitoring

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to your branch
5. Create a Pull Request

## License
[License details to be added]

## Support
For issues and questions, please create an issue in the repository.