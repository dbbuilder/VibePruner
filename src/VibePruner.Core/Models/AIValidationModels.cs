using System;
using System.Collections.Generic;

namespace VibePruner.Core.Models
{
    public class AIProviderConfiguration
    {
        public string Name { get; set; }
        public bool Enabled { get; set; }
        public string Model { get; set; }
        public int MaxTokens { get; set; }
        public double Temperature { get; set; }
        public string ApiKey { get; set; }
        public string Endpoint { get; set; }
        public TimeSpan Timeout { get; set; } = TimeSpan.FromSeconds(30);
        public int MaxRetries { get; set; } = 3;
    }

    public class AIValidationConfiguration
    {
        public bool Enabled { get; set; }
        public ConsensusRequirement RequiredAgreement { get; set; }
        public Dictionary<string, AIProviderConfiguration> Providers { get; set; } = new();
        public SafetyThresholds Safety { get; set; } = new();
        public ValidationPrompts Prompts { get; set; } = new();
    }

    public class SafetyThresholds
    {
        public double MinConfidence { get; set; } = 0.9;
        public int MaxBatchSize { get; set; } = 10;
        public int CooldownBetweenBatchesMs { get; set; } = 5000;
        public int MaxTokensPerBatch { get; set; } = 50000;
        public decimal MaxCostPerRun { get; set; } = 10.00m;
    }

    public class ValidationPrompts
    {
        public string SystemPrompt { get; set; } = @"You are an expert code analyst tasked with determining if files can be safely deleted from a codebase without causing issues.";
        
        public string FileAnalysisTemplate { get; set; } = @"
Analyze the following file for safe deletion:

File: {FilePath}
Type: {FileType}
Size: {FileSize}
Last Modified: {LastModified}
Dependencies (files this imports): {Dependencies}
Dependents (files that import this): {Dependents}

Content Preview:
{ContentPreview}

Related Files in Directory:
{RelatedFiles}

Question: Can this file be safely deleted without breaking the codebase?

Consider:
1. Hidden dependencies (reflection, dynamic imports, string references)
2. Build system references (makefiles, project files, scripts)
3. Documentation value
4. Test coverage implications
5. Configuration or deployment references

Respond with a JSON object:
{{
  ""status"": ""SAFE"" | ""UNSAFE"" | ""UNCERTAIN"",
  ""confidence"": 0.0-1.0,
  ""reasons"": [""reason1"", ""reason2""],
  ""warnings"": [""warning1"", ""warning2""]
}}";

        public Dictionary<string, string> FileTypePrompts { get; set; } = new()
        {
            ["test"] = "Pay special attention to shared test utilities and fixtures that other tests might depend on.",
            ["config"] = "Check for environment-specific configurations and deployment references.",
            ["migration"] = "Database migrations should almost never be deleted. Look for rollback dependencies.",
            ["interface"] = "API contracts and interfaces have high impact. Check all implementations.",
            ["documentation"] = "Assess if documentation is outdated or still provides value."
        };
    }

    public enum ConsensusRequirement
    {
        Single,      // Any provider says safe
        Majority,    // More than half say safe
        Unanimous    // All providers must agree
    }

    public class ValidationOverride
    {
        public string FilePath { get; set; }
        public OverrideAction Action { get; set; }
        public string Reason { get; set; }
        public string Author { get; set; }
        public DateTime Timestamp { get; set; }
    }

    public enum OverrideAction
    {
        ForceKeep,
        ForceDelete,
        RequireManualReview
    }

    public class AIValidationMetrics
    {
        public int TotalValidations { get; set; }
        public int TruePositives { get; set; }  // Correctly identified as safe to delete
        public int TrueNegatives { get; set; }  // Correctly identified as unsafe
        public int FalsePositives { get; set; } // Marked safe but caused issues
        public int FalseNegatives { get; set; } // Marked unsafe but were actually unused
        public Dictionary<string, ProviderMetrics> ProviderMetrics { get; set; } = new();
        public DateTime LastUpdated { get; set; }
    }

    public class ProviderMetrics
    {
        public string ProviderName { get; set; }
        public int TotalCalls { get; set; }
        public int SuccessfulCalls { get; set; }
        public int FailedCalls { get; set; }
        public long TotalTokensUsed { get; set; }
        public decimal TotalCost { get; set; }
        public double AverageConfidence { get; set; }
        public double AgreementRate { get; set; } // How often agrees with consensus
        public TimeSpan AverageResponseTime { get; set; }
    }
}