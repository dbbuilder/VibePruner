# VibePruner Python - Autonomous Development Protocol

## Project Overview
VibePruner is a Python-based intelligent file cleanup tool that safely prunes unnecessary files while protecting tests and critical code. We're enhancing it with AI-powered validation for maximum safety.

## Autonomous Development Protocol Active

This TODO follows the Autonomous Development Protocol with TDD methodology. Each task includes test-first implementation, comprehensive error handling, and incremental commits.

## Git Management Protocol
- Commit frequency: Every 15-30 minutes or logical unit completion
- Push frequency: Every 3-4 commits or major milestone
- Commit format: `type(scope): description` (feat, fix, test, refactor, docs)
- Always update .gitignore before commits

## Current Sprint Priority

### HIGH PRIORITY - AI Integration Foundation

- [ ] **Create AI provider abstraction layer** (est: 2h)
  - Write tests for provider interface
  - Design cloud-agnostic provider pattern
  - Support OpenAI, Anthropic Claude, Google Gemini
  - Implement provider factory
  - Git commits: `test(ai): add provider interface tests`, `feat(ai): implement provider abstraction`

- [ ] **Implement configuration management for AI** (est: 1.5h)
  - Write tests for AI configuration
  - Extend config.py with AI settings
  - Support environment variables for API keys
  - Add provider-specific configurations
  - Git commits: `test(config): add AI configuration tests`, `feat(config): add AI provider settings`

- [ ] **Create AI validation module** (est: 3h)
  - Write comprehensive tests for validation logic
  - Design FileValidationContext class
  - Implement consensus validation logic
  - Add safety thresholds and overrides
  - Git commits: `test(validation): add AI validation tests`, `feat(validation): implement consensus validator`

### MEDIUM PRIORITY - Provider Implementations

- [ ] **Implement OpenAI provider** (est: 2h)
  - Write tests for OpenAI integration
  - Handle API calls with retry logic
  - Implement token counting
  - Add response parsing
  - Git commits: `test(openai): add provider tests`, `feat(openai): implement GPT-4 provider`

- [ ] **Implement Anthropic Claude provider** (est: 2h)
  - Write tests for Claude integration
  - Handle Claude-specific API format
  - Implement streaming if needed
  - Add Claude-specific prompts
  - Git commits: `test(claude): add provider tests`, `feat(claude): implement Claude provider`

- [ ] **Implement Google Gemini provider** (est: 2h)
  - Write tests for Gemini integration
  - Handle Google API authentication
  - Implement Gemini-specific features
  - Add batch processing support
  - Git commits: `test(gemini): add provider tests`, `feat(gemini): implement Gemini provider`

### Integration with Existing VibePruner

- [ ] **Integrate AI validation into analyzer.py** (est: 3h)
  - Write tests for enhanced analyzer
  - Add AI validation step to analysis pipeline
  - Implement confidence scoring with AI input
  - Update file proposals with AI feedback
  - Git commits: `test(analyzer): add AI integration tests`, `feat(analyzer): integrate AI validation`

- [ ] **Update UI for AI feedback** (est: 2h)
  - Write tests for UI enhancements
  - Display AI validation results
  - Show provider consensus/disagreements
  - Add AI confidence indicators
  - Git commits: `test(ui): add AI display tests`, `feat(ui): show AI validation results`

- [ ] **Add AI validation to test_guardian.py** (est: 2h)
  - Write tests for guardian enhancements
  - Validate test-related files with extra care
  - Use AI to identify test dependencies
  - Git commits: `test(guardian): add AI validation tests`, `feat(guardian): enhance with AI validation`

### Cloud-Agnostic Infrastructure

- [ ] **Implement local model support** (est: 3h)
  - Write tests for local model interface
  - Add support for Ollama/LocalAI
  - Implement fallback to local models
  - Test with open-source models
  - Git commits: `test(local): add local model tests`, `feat(local): implement local AI support`

- [ ] **Create caching layer** (est: 2h)
  - Write tests for cache functionality
  - Implement file hash-based caching
  - Cache AI responses for identical files
  - Add cache expiration logic
  - Git commits: `test(cache): add caching tests`, `feat(cache): implement AI response cache`

- [ ] **Add cost tracking and limits** (est: 1.5h)
  - Write tests for cost tracking
  - Track tokens/requests per provider
  - Implement cost estimation
  - Add budget limits and warnings
  - Git commits: `test(cost): add tracking tests`, `feat(cost): implement usage tracking`

### Testing and Validation

- [ ] **Create mock AI providers for testing** (est: 1.5h)
  - Implement deterministic mock responses
  - Add configurable test scenarios
  - Support failure simulation
  - Git commits: `test(mocks): add AI provider mocks`

- [ ] **Add integration tests** (est: 2h)
  - Test full pipeline with AI validation
  - Test provider failover scenarios
  - Test consensus disagreements
  - Git commits: `test(integration): add end-to-end AI tests`

- [ ] **Performance benchmarking** (est: 1.5h)
  - Benchmark with/without AI validation
  - Test batch processing performance
  - Optimize token usage
  - Git commits: `test(perf): add performance benchmarks`

### Documentation and Examples

- [ ] **Update README with AI features** (est: 1h)
  - Document AI provider setup
  - Add configuration examples
  - Include cost considerations
  - Git commits: `docs(readme): add AI validation documentation`

- [ ] **Create AI configuration guide** (est: 1.5h)
  - Provider-specific setup instructions
  - Best practices for prompts
  - Troubleshooting guide
  - Git commits: `docs(guide): add AI configuration guide`

## Implementation Architecture

### 1. AI Provider Interface (`ai_providers/base.py`)
```python
class AIProvider(ABC):
    @abstractmethod
    async def validate_file_deletion(self, context: FileValidationContext) -> ValidationResult:
        pass
```

### 2. Provider Implementations
- `ai_providers/openai_provider.py`
- `ai_providers/claude_provider.py`
- `ai_providers/gemini_provider.py`
- `ai_providers/local_provider.py`

### 3. Validation Module (`ai_validation.py`)
```python
class ConsensusValidator:
    def __init__(self, providers: List[AIProvider], config: AIConfig):
        self.providers = providers
        self.config = config
    
    async def validate_files(self, files: List[FileInfo]) -> List[ValidationResult]:
        # Implement consensus logic
```

### 4. Configuration Extension (`config.py`)
```python
ai_config = {
    "enabled": True,
    "providers": {
        "openai": {"api_key": "env:OPENAI_API_KEY", "model": "gpt-4"},
        "claude": {"api_key": "env:CLAUDE_API_KEY", "model": "claude-3"},
        "gemini": {"api_key": "env:GEMINI_API_KEY", "model": "gemini-pro"}
    },
    "consensus_mode": "majority",  # unanimous, majority, any
    "max_cost_per_run": 5.00,
    "cache_ttl_hours": 24
}
```

## Testing Strategy

1. **Unit Tests**: Each provider and module
2. **Integration Tests**: Full pipeline with mocked providers
3. **Cost Tests**: Ensure we stay within budget
4. **Performance Tests**: Validation doesn't slow down analysis
5. **Failure Tests**: Provider failures don't break the tool

## Deployment Considerations

- **Environment Variables**: All API keys in env vars
- **Fallback Logic**: Local models if cloud fails
- **Rate Limiting**: Respect provider limits
- **Error Recovery**: Continue without AI if needed

## Success Metrics

- Zero false positives (important files deleted)
- <5% false negatives (unnecessary files kept)
- <2 second overhead per file for AI validation
- Stay under $0.01 per file analyzed
- 90%+ cache hit rate for duplicate files

## Completed Tasks
- [x] Repository cleaned of C# implementation
- [x] Python implementation moved to main directory

## Notes for Autonomous Execution

1. **Always start with tests** - TDD approach
2. **Keep it cloud-agnostic** - No vendor lock-in
3. **Fail gracefully** - Tool works without AI
4. **Cache aggressively** - Minimize API costs
5. **Log everything** - Full audit trail
6. **Stay backwards compatible** - Existing users unaffected

Remember: "Progress over perfection" - Ship working increments frequently.