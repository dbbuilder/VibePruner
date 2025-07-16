namespace VibePruner.Core.Models
{
    /// <summary>
    /// Represents the result of analyzing a file
    /// </summary>
    public class FileAnalysisResult
    {
        public Guid Id { get; set; }
        public Guid FileItemId { get; set; }
        public DateTime AnalysisDate { get; set; }
        public string AnalysisType { get; set; } = string.Empty;
        public bool Success { get; set; }
        public string? ErrorMessage { get; set; }
        public int TokenCount { get; set; }
        public int LineCount { get; set; }
        public int CharacterCount { get; set; }
        public Dictionary<string, object> Metadata { get; set; } = new();
        
        // Navigation property
        public FileItem FileItem { get; set; } = null!;
    }
}