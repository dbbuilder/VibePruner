using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace VibePruner.Core.Interfaces
{
    public interface IAIValidator
    {
        string ProviderName { get; }
        Task<FileValidationResult> ValidateFileDeletionAsync(
            FileValidationContext context,
            CancellationToken cancellationToken = default);
    }

    public interface IConsensusValidator
    {
        Task<ConsensusValidationResult> ValidateFileAsync(
            FileValidationContext context,
            CancellationToken cancellationToken = default);
        
        Task<BatchValidationResult> ValidateBatchAsync(
            IEnumerable<FileValidationContext> contexts,
            CancellationToken cancellationToken = default);
    }

    public class FileValidationContext
    {
        public string FilePath { get; set; }
        public string FileContent { get; set; }
        public string FileType { get; set; }
        public long FileSize { get; set; }
        public DateTime LastModified { get; set; }
        public List<string> Dependencies { get; set; } = new();
        public List<string> Dependents { get; set; } = new();
        public List<string> RelatedFiles { get; set; } = new();
        public Dictionary<string, object> Metadata { get; set; } = new();
    }

    public class FileValidationResult
    {
        public ValidationStatus Status { get; set; }
        public double Confidence { get; set; }
        public List<string> Reasons { get; set; } = new();
        public List<string> Warnings { get; set; } = new();
        public string ProviderName { get; set; }
        public TimeSpan ValidationDuration { get; set; }
        public int TokensUsed { get; set; }
    }

    public class ConsensusValidationResult
    {
        public string FilePath { get; set; }
        public bool CanDelete { get; set; }
        public double AverageConfidence { get; set; }
        public ValidationStatus ConsensusStatus { get; set; }
        public List<FileValidationResult> ProviderResults { get; set; } = new();
        public List<string> ConsolidatedReasons { get; set; } = new();
        public List<string> ConsolidatedWarnings { get; set; } = new();
        public TimeSpan TotalValidationTime { get; set; }
    }

    public class BatchValidationResult
    {
        public List<ConsensusValidationResult> Results { get; set; } = new();
        public int TotalFiles { get; set; }
        public int SafeToDelete { get; set; }
        public int UnsafeToDelete { get; set; }
        public int Uncertain { get; set; }
        public Dictionary<string, int> TokenUsageByProvider { get; set; } = new();
        public TimeSpan TotalDuration { get; set; }
    }

    public enum ValidationStatus
    {
        Safe,
        Unsafe,
        Uncertain,
        Error,
        Skipped
    }
}