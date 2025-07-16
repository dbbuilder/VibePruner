# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the VibePruner project.

## Project Overview

VibePruner is a Python-based intelligent file cleanup tool that safely identifies and archives unnecessary files while protecting tests and critical code. The project is being enhanced with AI-powered validation using multiple providers (OpenAI, Claude, Gemini) in a cloud-agnostic manner.

## Key Architecture Components

### Core Modules
- **vibepruner.py**: Main entry point and orchestration
- **analyzer.py**: File dependency analysis and scoring
- **test_guardian.py**: Test protection and validation
- **ui.py**: Rich-based terminal UI for interactive review
- **config.py**: Configuration management with environment variable support
- **session_manager.py**: Tracks analysis sessions
- **rollback_manager.py**: Handles safe archiving and restoration

### AI Integration (In Development)
- **ai_providers/**: Provider abstraction layer
  - Base interface for all AI providers
  - OpenAI, Claude, Gemini implementations
  - Local model support (Ollama/LocalAI)
- **ai_validation.py**: Consensus validation logic
- **ai_cache.py**: Response caching to minimize API costs

## Development Commands

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run type checking (when added)
mypy .

# Format code
black .

# Lint code
flake8 .

# Install in development mode
pip install -e .

# Run VibePruner
python vibepruner.py /path/to/project
```

## Testing Strategy

- Write tests first (TDD approach)
- Mock AI providers for deterministic tests
- Test both success and failure scenarios
- Ensure backward compatibility

## AI Integration Guidelines

### Provider Implementation Pattern
```python
class AIProvider(ABC):
    @abstractmethod
    async def validate_file_deletion(self, context: FileValidationContext) -> ValidationResult:
        pass
```

### Consensus Logic
- Default to "majority" consensus mode
- Support "unanimous" for high-risk operations
- Always fail-safe (keep file if uncertain)

### Cost Management
- Cache responses based on file hash
- Batch similar files together
- Use cheaper models for initial screening
- Track token usage and costs

## Configuration Patterns

### Environment Variables
- All API keys in environment variables
- Support `.env` file for local development
- Never commit secrets

### Config File Structure
```json
{
  "ai_validation": {
    "enabled": true,
    "providers": {...},
    "consensus_mode": "majority",
    "max_cost_per_run": 5.00
  }
}
```

## Safety Principles

1. **Never Delete**: Only archive files
2. **Test First**: Always validate tests still pass
3. **User Approval**: Require explicit confirmation
4. **Easy Rollback**: One-command restoration
5. **AI Consensus**: Multiple providers must agree

## Common Tasks

### Adding a New AI Provider
1. Create `ai_providers/newprovider.py`
2. Implement the `AIProvider` interface
3. Add configuration in `config.py`
4. Write comprehensive tests
5. Update documentation

### Debugging File Analysis
1. Check `vibepruner.log` for detailed logs
2. Use `--verbose` flag for more output
3. Examine `.vibepruner/` directory for session data
4. Review dependency graph in analyzer output

## Performance Considerations

- File analysis can be I/O intensive
- AI validation adds latency (mitigate with caching)
- Large projects may need batch processing
- Consider async/await for I/O operations

## Known Issues and Workarounds

- Symbolic links: Currently follows them (TODO: make configurable)
- Binary files: Detected by extension and content sampling
- Large files: Truncated for AI analysis (configurable limit)
- Unicode filenames: Properly handled in Python 3

## Development Workflow

1. Pick task from TODO.md
2. Write failing tests
3. Implement feature
4. Ensure all tests pass
5. Update documentation
6. Commit with conventional format: `type(scope): description`
7. Push every 3-4 commits

## Cloud-Agnostic Design

- No vendor lock-in
- Support local models
- Abstract provider interfaces
- Configuration-driven provider selection
- Graceful fallback without AI