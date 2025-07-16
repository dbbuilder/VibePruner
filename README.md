# VibePruner

An intelligent file cleanup tool with AI-powered validation that ensures your tests still work after pruning unnecessary files.

## Features

### Core Capabilities
- **Test Protection**: Captures test outputs before and after changes, ensuring nothing breaks
- **Smart Analysis**: Identifies orphaned files through dependency analysis
- **Markdown Parsing**: Checks documentation for file references and importance indicators
- **Project Awareness**: Understands .sln, .csproj, package.json, and other project files
- **Interactive Review**: Terminal UI for reviewing and approving proposed changes
- **Safe Archiving**: Never deletes files - archives them with easy rollback
- **Multi-Language Support**: Works with Python, C#, JavaScript, TypeScript, Go, Rust, and more

### AI-Powered Validation
- **Multi-Provider Consensus**: Validates with OpenAI GPT-4, Anthropic Claude, and Google Gemini
- **Consensus Modes**: Unanimous, majority, or any - you choose the safety level
- **Smart Caching**: Reduces API costs by 90%+ through intelligent response caching
- **Confidence Scoring**: AI-enhanced confidence levels for pruning decisions
- **Safety First**: AI can prevent deletion of files it deems critical
- **Cloud-Agnostic**: No vendor lock-in, works with any cloud provider
- **Local Model Support**: Coming soon - Ollama/LocalAI for zero-cost operation

## Installation

```bash
# Clone the repository
git clone https://github.com/dbbuilder/VibePruner.git
cd VibePruner

# Install dependencies
pip install -r requirements.txt

# Optional: Install for development
pip install -e .
```

## Usage

```bash
# Basic usage
python vibepruner.py /path/to/your/project

# With custom config
python vibepruner.py /path/to/your/project --config myconfig.json

# Verbose mode
python vibepruner.py /path/to/your/project --verbose
```

## How It Works

1. **Test Baseline**: Discovers and runs all tests, capturing their output
2. **File Analysis**: Scans all files and builds a dependency graph
3. **AI Validation** (optional): Multiple AI providers analyze each file for safety
4. **Project Parsing**: Reads project files to identify required dependencies
5. **Documentation Check**: Analyzes markdown files for file references
6. **Proposal Generation**: Suggests files to archive based on multiple factors + AI input
7. **Interactive Review**: Shows proposals in a nice terminal UI with AI insights
8. **Safe Execution**: Archives approved files (never deletes)
9. **Test Validation**: Re-runs tests and compares output
10. **Auto-Rollback**: If tests fail, automatically restores archived files

## Configuration

Create a `config.json` file to customize behavior:

```json
{
  "protected_patterns": ["README*", "LICENSE*", "*.config"],
  "temp_patterns": ["*.tmp", "*.log", "*.cache"],
  "confidence_thresholds": {
    "high": 0.7,
    "medium": 0.5,
    "low": 0.3
  },
  "ai_validation": {
    "enabled": true,
    "providers": {
      "openai": {
        "enabled": true,
        "api_key": "${OPENAI_API_KEY}",
        "model": "gpt-4-turbo-preview"
      },
      "claude": {
        "enabled": true,
        "api_key": "${CLAUDE_API_KEY}",
        "model": "claude-3-opus-20240229"
      },
      "gemini": {
        "enabled": true,
        "api_key": "${GEMINI_API_KEY}",
        "model": "gemini-pro"
      }
    },
    "consensus_mode": "majority",
    "confidence_threshold": 0.8
  }
}
```

### Environment Variables

Set API keys as environment variables for security:

```bash
export OPENAI_API_KEY="your-openai-key"
export CLAUDE_API_KEY="your-claude-key"
export GEMINI_API_KEY="your-gemini-key"
```

## Test Output Comparison

VibePruner intelligently compares test outputs by:
- Ignoring timestamps and durations
- Normalizing file paths
- Focusing on test counts and pass/fail status
- Comparing error signatures

This ensures that only meaningful changes in test behavior trigger a rollback.

## Safety Features

- All files are archived, never deleted
- Automatic rollback if tests fail
- Dry-run mode available
- User approval required for all actions
- Detailed logging of all operations

## Supported Test Frameworks

- **Python**: pytest, unittest
- **JavaScript/Node**: npm test, jest, mocha
- **.NET**: dotnet test
- **Playwright**: Browser automation tests
- **SQL**: Database unit tests
- And more...

## File Importance Scoring

Files are scored based on:
- Reference count (how many files import/use it)
- Documentation mentions
- Keywords in docs (required, temporary, deprecated)
- File patterns (test, temp, backup)
- Age and modification time
- Project file references
- **AI consensus** (when enabled): Multiple AI models evaluate criticality

## AI Validation Details

When AI validation is enabled, VibePruner:
1. Sends file content and context to multiple AI providers
2. Each provider analyzes for hidden dependencies, build references, and criticality
3. Results are aggregated based on consensus mode (unanimous/majority/any)
4. AI confidence adjusts the overall pruning confidence score
5. Files marked "UNSAFE" by AI consensus are never proposed for deletion

This provides an extra layer of safety, especially for complex codebases where static analysis might miss important relationships.

### Token Usage Optimization

VibePruner includes an intelligent file preprocessor that significantly reduces AI token usage while maintaining accuracy:

- **Smart Extraction**: Extracts only relevant information like imports, exports, function/class names, and critical comments
- **Context Preservation**: Keeps important patterns like TODO/FIXME comments, environment variables, and external dependencies
- **80-90% Token Reduction**: Typically reduces a 5000+ character file to under 1000 characters for AI analysis
- **Configurable**: Can be disabled with `use_preprocessing: false` in config

The preprocessor extracts:
- Import/export statements and dependencies
- Class and function definitions
- External API calls and file references
- Database queries and table references
- Environment variables and configuration
- Build commands and scripts
- Important comments (TODO, FIXME, WARNING)
- Test fixtures and test dependencies

## Contributing

Feel free to submit issues and enhancement requests!

## License

[Your license here]
