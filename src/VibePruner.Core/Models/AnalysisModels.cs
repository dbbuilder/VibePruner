namespace VibePruner.Core.Models
{
    /// <summary>
    /// Result of analyzing markdown files
    /// </summary>
    public class MarkdownAnalysisResult
    {
        public Dictionary<string, List<FileReference>> FileReferences { get; set; } = new();
        public Dictionary<string, FileImportanceInfo> FileImportance { get; set; } = new();
        public List<string> RequiredFiles { get; set; } = new();
        public List<string> TemporaryFiles { get; set; } = new();
        public List<string> DeprecatedFiles { get; set; } = new();
    }
    
    /// <summary>
    /// Information about a file's importance based on documentation
    /// </summary>
    public class FileImportanceInfo
    {
        public string FilePath { get; set; } = string.Empty;
        public ImportanceLevel Importance { get; set; }
        public List<string> Reasons { get; set; } = new();
        public List<string> MentionedInFiles { get; set; } = new();
        public Dictionary<string, int> KeywordMatches { get; set; } = new();
    }
    
    /// <summary>
    /// Importance levels for files
    /// </summary>
    public enum ImportanceLevel
    {
        Critical,
        Required,
        Standard,
        Optional,
        Temporary,
        Deprecated
    }
    
    /// <summary>
    /// Represents project file analysis results
    /// </summary>
    public class ProjectFileAnalysisResult
    {
        public List<string> ProjectFiles { get; set; } = new();
        public List<string> ReferencedFiles { get; set; } = new();
        public List<string> PackageFiles { get; set; } = new();
        public List<string> BuildFiles { get; set; } = new();
        public Dictionary<string, List<string>> ProjectDependencies { get; set; } = new();
        public List<string> EntryPoints { get; set; } = new();
    }
}