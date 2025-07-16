namespace VibePruner.Core.Models
{
    /// <summary>
    /// Represents a logged operation for tracking and learning
    /// </summary>
    public class OperationLog
    {
        public Guid Id { get; set; }
        public Guid SessionId { get; set; }
        public DateTime Timestamp { get; set; }
        public OperationType OperationType { get; set; }
        public string FilePath { get; set; } = string.Empty;
        public FileAction Action { get; set; }
        public string Reason { get; set; } = string.Empty;
        public bool UserApproved { get; set; }
        public string? UserReason { get; set; }
        public bool Success { get; set; }
        public string? ErrorMessage { get; set; }
        public TimeSpan Duration { get; set; }
        public Dictionary<string, object> AdditionalData { get; set; } = new();
    }
    
    /// <summary>
    /// Types of operations
    /// </summary>
    public enum OperationType
    {
        Scan,
        Analyze,
        Propose,
        Execute,
        Validate,
        Rollback
    }
    
    /// <summary>
    /// Project profile for learning patterns
    /// </summary>
    public class ProjectProfile
    {
        public Guid Id { get; set; }
        public string ProjectType { get; set; } = string.Empty; // e.g., "DotNet", "Node", "Python"
        public Dictionary<string, double> FilePatternWeights { get; set; } = new();
        public List<string> CommonlyProtectedPatterns { get; set; } = new();
        public List<string> CommonlyArchivedPatterns { get; set; } = new();
        public Dictionary<string, int> UserOverrideFrequency { get; set; } = new();
        public DateTime LastUpdated { get; set; }
        public int SessionCount { get; set; }
    }
    
    /// <summary>
    /// Learning metrics for improving decisions
    /// </summary>
    public class LearningMetrics
    {
        public Guid Id { get; set; }
        public string MetricType { get; set; } = string.Empty;
        public double AccuracyRate { get; set; }
        public double UserAgreementRate { get; set; }
        public int SampleSize { get; set; }
        public Dictionary<string, double> FeatureImportance { get; set; } = new();
        public DateTime CalculatedDate { get; set; }
    }
}