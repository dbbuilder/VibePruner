namespace VibePruner.Core.Models
{
    /// <summary>
    /// Represents a proposed file action for user review
    /// </summary>
    public class ProposedFileAction
    {
        public Guid Id { get; set; }
        public string FilePath { get; set; } = string.Empty;
        public string RelativePath { get; set; } = string.Empty;
        public FileAction Action { get; set; }
        public string Reason { get; set; } = string.Empty;
        public double ConfidenceScore { get; set; }
        public Dictionary<string, double> FactorScores { get; set; } = new();
        public bool UserApproved { get; set; }
        public string? UserReason { get; set; }
        public DateTime ProposedDate { get; set; }
        public string? TargetPath { get; set; } // For moves/archives
        public List<string> RelatedFiles { get; set; } = new(); // For consolidations
    }
    
    /// <summary>
    /// Types of file actions
    /// </summary>
    public enum FileAction
    {
        Keep,
        Archive,
        Delete,
        Consolidate,
        Move,
        Rename
    }
    
    /// <summary>
    /// Represents a tree node for the UI
    /// </summary>
    public class FileTreeNode
    {
        public string Id { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public string Path { get; set; } = string.Empty;
        public bool IsDirectory { get; set; }
        public FileAction? ProposedAction { get; set; }
        public string? ActionReason { get; set; }
        public double? ConfidenceScore { get; set; }
        public bool UserApproved { get; set; } = true;
        public string? UserComment { get; set; }
        public List<FileTreeNode> Children { get; set; } = new();
        public Dictionary<string, object> Metadata { get; set; } = new();
    }
    
    /// <summary>
    /// Represents an analysis session for tracking
    /// </summary>
    public class AnalysisSession
    {
        public Guid Id { get; set; }
        public string ProjectPath { get; set; } = string.Empty;
        public string ProjectName { get; set; } = string.Empty;
        public DateTime StartTime { get; set; }
        public DateTime? EndTime { get; set; }
        public string Username { get; set; } = string.Empty;
        public int TotalFiles { get; set; }
        public int FilesProcessed { get; set; }
        public Dictionary<FileAction, int> ActionCounts { get; set; } = new();
        public List<ProposedFileAction> ProposedActions { get; set; } = new();
        public SessionStatus Status { get; set; }
    }
    
    /// <summary>
    /// Status of an analysis session
    /// </summary>
    public enum SessionStatus
    {
        InProgress,
        WaitingForApproval,
        Executing,
        Completed,
        Failed,
        RolledBack
    }
}