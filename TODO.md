# VibePruner Development TODO

## Project Status: Python Implementation with AI Enhancement

VibePruner is now a Python-based tool with upcoming AI-powered validation features for safer file pruning.

## Immediate Priority - AI Integration

### Phase 1: Foundation (Week 1)
- [ ] **AI Provider Abstraction Layer**
  - [ ] Create `ai_providers/` module structure
  - [ ] Design base provider interface
  - [ ] Implement provider factory pattern
  - [ ] Add configuration management for AI settings

- [ ] **Core AI Validation Module**
  - [ ] Build FileValidationContext class
  - [ ] Implement consensus validation logic
  - [ ] Add safety thresholds and confidence scoring
  - [ ] Create validation result aggregation

### Phase 2: Provider Implementation (Week 1-2)
- [ ] **OpenAI Integration**
  - [ ] Implement GPT-4 provider
  - [ ] Add retry logic and error handling
  - [ ] Token counting and cost tracking
  - [ ] Response parsing and validation

- [ ] **Anthropic Claude Integration**
  - [ ] Implement Claude-3 provider
  - [ ] Handle Claude-specific API patterns
  - [ ] Add specialized prompts for code analysis
  - [ ] Streaming support if beneficial

- [ ] **Google Gemini Integration**
  - [ ] Implement Gemini Pro provider
  - [ ] Handle Google authentication
  - [ ] Batch processing optimization
  - [ ] Cost-effective screening logic

- [ ] **Local Model Support (Ollama/LocalAI)**
  - [ ] Add local model interface
  - [ ] Implement fallback logic
  - [ ] Test with Code Llama, Mixtral
  - [ ] Zero-cost validation option

### Phase 3: Integration (Week 2)
- [ ] **Enhance File Analyzer**
  - [ ] Integrate AI validation into analysis pipeline
  - [ ] Update confidence scoring with AI input
  - [ ] Add AI-based dependency detection
  - [ ] Implement caching for repeated files

- [ ] **Update Interactive UI**
  - [ ] Display AI validation results
  - [ ] Show provider consensus/conflicts
  - [ ] Add confidence indicators
  - [ ] Provider-specific explanations

- [ ] **Test Guardian Enhancement**
  - [ ] Extra validation for test files
  - [ ] AI-powered test dependency detection
  - [ ] Identify test utilities and fixtures
  - [ ] Prevent breaking test infrastructure

### Phase 4: Testing & Documentation (Week 2-3)
- [ ] **Comprehensive Testing**
  - [ ] Unit tests for all AI providers
  - [ ] Integration tests with mocked responses
  - [ ] Performance benchmarking
  - [ ] Cost tracking validation
  - [ ] Failure scenario testing

- [ ] **Documentation Update**
  - [ ] AI setup guide
  - [ ] Provider comparison matrix
  - [ ] Cost optimization tips
  - [ ] Troubleshooting guide
  - [ ] Example configurations

## Existing Features to Maintain

### Core Functionality ✅
- [x] File dependency analysis
- [x] Test protection with output comparison
- [x] Markdown documentation parsing
- [x] Project file understanding (.sln, package.json, etc.)
- [x] Interactive terminal UI
- [x] Safe archiving with rollback
- [x] Multi-language support

### Safety Features ✅
- [x] Never delete, only archive
- [x] Automatic rollback on test failure
- [x] User approval required
- [x] Detailed audit logging
- [x] Dry-run mode

## Future Enhancements

### Performance Optimization
- [ ] Parallel file analysis
- [ ] Incremental analysis mode
- [ ] Distributed processing support
- [ ] Analysis result caching

### Extended AI Features
- [ ] Custom prompt templates per project type
- [ ] Learning from user decisions
- [ ] Project-specific model fine-tuning
- [ ] AI-powered refactoring suggestions

### Integration Options
- [ ] VS Code extension
- [ ] GitHub Action
- [ ] Pre-commit hook
- [ ] CI/CD pipeline integration

### Advanced Safety
- [ ] Git integration for safer operations
- [ ] Branch-based analysis
- [ ] Dependency graph visualization
- [ ] Impact analysis reports

## Technical Debt
- [ ] Improve test coverage (target: 90%)
- [ ] Add type hints throughout
- [ ] Performance profiling
- [ ] Memory usage optimization for large projects
- [ ] Async/await for I/O operations

## Bug Fixes
- [ ] Handle symbolic links properly
- [ ] Improve binary file detection
- [ ] Better handling of permission errors
- [ ] Fix Unicode filename issues

## Configuration Schema
```python
{
    "ai_validation": {
        "enabled": True,
        "providers": {
            "openai": {
                "enabled": True,
                "api_key": "${OPENAI_API_KEY}",
                "model": "gpt-4-turbo-preview",
                "max_tokens": 4000,
                "temperature": 0.2
            },
            "claude": {
                "enabled": True,
                "api_key": "${CLAUDE_API_KEY}",
                "model": "claude-3-opus-20240229",
                "max_tokens": 4000
            },
            "gemini": {
                "enabled": True,
                "api_key": "${GEMINI_API_KEY}",
                "model": "gemini-pro",
                "max_tokens": 4000
            },
            "local": {
                "enabled": False,
                "endpoint": "http://localhost:11434",
                "model": "codellama:13b"
            }
        },
        "consensus_mode": "majority",
        "confidence_threshold": 0.8,
        "max_cost_per_run": 5.00,
        "cache_ttl_hours": 24,
        "batch_size": 10
    }
}
```

## Development Guidelines

1. **Test-Driven Development**: Write tests first
2. **Cloud-Agnostic**: No vendor lock-in
3. **Backward Compatible**: Don't break existing functionality
4. **Performance Conscious**: Monitor API costs and latency
5. **User-Friendly**: Clear feedback and explanations

## Success Metrics

- **Safety**: Zero critical files deleted
- **Accuracy**: >95% correct pruning decisions
- **Performance**: <2s overhead per file
- **Cost**: <$0.01 per file analyzed
- **User Satisfaction**: Clear explanations for all decisions

## Notes

- All API keys should be environment variables
- Local model support ensures zero-cost option
- Caching reduces API calls by 90%+
- Consensus mode prevents single-provider errors
- Tool remains functional without AI (fallback mode)