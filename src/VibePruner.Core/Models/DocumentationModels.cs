namespace VibePruner.Core.Models
{
    /// <summary>
    /// Types of documentation
    /// </summary>
    public enum DocumentationType
    {
        Readme,
        ApiDocumentation,
        UserGuide,
        DeveloperGuide,
        Changelog,
        Contributing,
        License,
        Configuration,
        Other
    }
    
    /// <summary>
    /// Represents documentation content
    /// </summary>
    public class DocumentContent
    {
        public string FilePath { get; set; } = string.Empty;
        public string Content { get; set; } = string.Empty;
        public DocumentationType Type { get; set; }
        public int TokenCount { get; set; }
        public DateTime LastModified { get; set; }
    }
    
    /// <summary>
    /// Result of documentation analysis
    /// </summary>
    public class DocumentationAnalysis
    {
        public string Summary { get; set; } = string.Empty;
        public DocumentationType DetectedType { get; set; }
        public List<string> KeyTopics { get; set; } = new();
        public double QualityScore { get; set; }
        public List<string> ImprovementSuggestions { get; set; } = new();
        public Dictionary<string, double> SimilarityScores { get; set; } = new();
    }
    
    /// <summary>
    /// Suggestion for consolidating documents
    /// </summary>
    public class ConsolidationSuggestion
    {
        public List<DocumentGroup> Groups { get; set; } = new();
        public string ConsolidationStrategy { get; set; } = string.Empty;
        public List<string> Warnings { get; set; } = new();
    }
    
    /// <summary>
    /// Group of documents that can be consolidated
    /// </summary>
    public class DocumentGroup
    {
        public string GroupName { get; set; } = string.Empty;
        public List<string> FilePaths { get; set; } = new();
        public string SuggestedFileName { get; set; } = string.Empty;
        public string ConsolidationReason { get; set; } = string.Empty;
        public double ConfidenceScore { get; set; }
    }
}