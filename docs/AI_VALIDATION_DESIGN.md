# AI-Assisted File Validation Design

## Overview

VibePruner integrates OpenAI, Claude, and Gemini APIs to provide multi-layer validation before pruning files. This ensures we only remove truly ancillary and unneeded files, minimizing the risk of breaking codebases.

## Core Principle

**Never delete a file unless multiple AI models agree it's safe to remove.**

## Multi-Stage AI Validation Pipeline

### Stage 1: Initial File Analysis
1. **Dependency Graph Analysis** (Local)
   - Parse import/include statements
   - Build reference graph
   - Identify orphaned files with zero incoming references

2. **Content Classification** (Local)
   - Categorize files: source code, tests, documentation, config, assets
   - Apply different validation rules per category
   - Flag protected patterns from configuration

### Stage 2: AI Context Analysis
For each candidate file for removal, gather context:
- File content (up to token limit)
- Directory structure around the file
- Related files (same directory, similar names)
- Git history (last modified, commit frequency)
- Dependencies (what it imports, what imports it)

### Stage 3: Multi-Provider Validation

#### Claude API Integration
```csharp
public interface IClaudeValidator
{
    Task<FileValidationResult> ValidateFileDeletion(
        FileContext context,
        string prompt = "Analyze if this file can be safely deleted"
    );
}
```

Claude excels at:
- Understanding complex code relationships
- Identifying subtle dependencies
- Recognizing architectural patterns

#### OpenAI GPT-4 Integration
```csharp
public interface IOpenAIValidator
{
    Task<FileValidationResult> ValidateFileDeletion(
        FileContext context,
        string systemPrompt = "You are a code safety analyst"
    );
}
```

GPT-4 strengths:
- General programming knowledge
- Cross-language expertise
- Documentation analysis

#### Gemini Integration
```csharp
public interface IGeminiValidator
{
    Task<FileValidationResult> ValidateFileDeletion(
        FileContext context,
        bool useCodeModel = true
    );
}
```

Gemini advantages:
- Fast inference for large batches
- Good at pattern recognition
- Cost-effective for initial screening

### Stage 4: Consensus Decision Making

```csharp
public class ConsensusValidator
{
    private readonly IClaudeValidator _claude;
    private readonly IOpenAIValidator _openai;
    private readonly IGeminiValidator _gemini;
    
    public async Task<ValidationDecision> ValidateFile(FileContext context)
    {
        var tasks = new[]
        {
            _claude.ValidateFileDeletion(context),
            _openai.ValidateFileDeletion(context),
            _gemini.ValidateFileDeletion(context)
        };
        
        var results = await Task.WhenAll(tasks);
        
        return new ValidationDecision
        {
            CanDelete = results.All(r => r.IsSafeToDelete),
            Confidence = results.Average(r => r.Confidence),
            Reasons = results.SelectMany(r => r.Reasons).Distinct(),
            Warnings = results.SelectMany(r => r.Warnings).Distinct()
        };
    }
}
```

## Validation Rules

### Always Keep (Override AI)
- Files matching protected patterns
- Recently modified files (configurable threshold)
- Files with active Git branches
- Entry points (main, index, app)
- Configuration files (unless explicitly targeted)

### High-Risk Categories (Require Unanimous Agreement)
- Database migrations
- API contracts/interfaces
- Authentication/authorization code
- Deployment configurations
- Test fixtures and utilities

### Safe Categories (Majority Agreement)
- Orphaned documentation
- Obsolete assets
- Generated files (with source available)
- Empty files
- Duplicate files

## AI Prompt Engineering

### Context-Rich Prompts
```
Analyze the following file for safe deletion:

File: {filepath}
Type: {filetype}
Last Modified: {date}
Dependencies: {list}
Dependents: {list}

Content Preview:
{first_500_lines}

Related Files:
{nearby_files}

Question: Is this file safe to delete without breaking the codebase?
Consider:
1. Hidden dependencies (reflection, dynamic imports)
2. Build system references
3. Documentation value
4. Historical importance
5. Potential future use

Respond with:
- SAFE/UNSAFE/UNCERTAIN
- Confidence: 0-100
- Reasons: [list]
- Warnings: [list]
```

### Specialized Prompts by File Type
- **Test Files**: Check for test utilities, shared fixtures
- **Config Files**: Verify no active references
- **Documentation**: Assess current relevance
- **Assets**: Check for hardcoded references
- **Source Code**: Deep dependency analysis

## Safety Mechanisms

### 1. Dry Run Mode
- Always default to dry run
- Generate detailed reports before any deletion
- Require explicit confirmation for destructive operations

### 2. Incremental Validation
- Start with lowest-risk files
- Build confidence through successful operations
- Stop at first sign of problems

### 3. Rollback Capability
- Archive files before deletion
- Maintain deletion manifest
- Easy restore functionality

### 4. Human Override
```csharp
public class ValidationOverride
{
    public string FilePath { get; set; }
    public OverrideAction Action { get; set; } // ForceKeep, ForceDelete
    public string Reason { get; set; }
    public DateTime Timestamp { get; set; }
}
```

## Implementation Priority

1. **Phase 1**: Local dependency analysis only
2. **Phase 2**: Single AI provider validation (start with Claude)
3. **Phase 3**: Multi-provider consensus
4. **Phase 4**: Machine learning from outcomes

## Cost Optimization

### Token Management
- Batch similar files together
- Cache validation results
- Use cheaper models for initial screening
- Reserve expensive models for high-risk decisions

### Prompt Optimization
- Compress file content intelligently
- Focus on relevant code sections
- Reuse analysis across similar files

## Metrics and Monitoring

Track:
- False positive rate (files marked safe but caused issues)
- False negative rate (files kept but were truly unused)
- AI agreement rates
- Token usage per provider
- Validation time per file

## Configuration

```json
{
  "AIValidation": {
    "Enabled": true,
    "RequiredAgreement": "Unanimous", // Majority, Unanimous, Single
    "Providers": {
      "Claude": {
        "Enabled": true,
        "Model": "claude-3-opus-20240229",
        "MaxTokens": 4096,
        "Temperature": 0.2
      },
      "OpenAI": {
        "Enabled": true,
        "Model": "gpt-4-turbo-preview",
        "MaxTokens": 4096,
        "Temperature": 0.2
      },
      "Gemini": {
        "Enabled": true,
        "Model": "gemini-pro",
        "MaxTokens": 4096,
        "Temperature": 0.2
      }
    },
    "SafetyThresholds": {
      "MinConfidence": 0.9,
      "MaxBatchSize": 10,
      "CooldownBetweenBatches": 5000
    }
  }
}
```

## Error Handling

- API failures: Fall back to more conservative decisions
- Timeout handling: Skip AI validation, mark as uncertain
- Rate limiting: Implement exponential backoff
- Budget limits: Stop when threshold reached

## Future Enhancements

1. **Learning System**: Track outcomes and improve prompts
2. **Custom Models**: Fine-tune models on successful validations
3. **IDE Integration**: Real-time validation in development
4. **Git Integration**: Validate before commits
5. **Language-Specific Models**: Specialized validators per language