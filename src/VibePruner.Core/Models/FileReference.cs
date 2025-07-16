namespace VibePruner.Core.Models
{
    /// <summary>
    /// Represents a reference between two files
    /// </summary>
    public class FileReference
    {
        public Guid Id { get; set; }
        public Guid SourceFileId { get; set; }
        public Guid TargetFileId { get; set; }
        public ReferenceType ReferenceType { get; set; }
        public string ReferenceText { get; set; } = string.Empty;
        public int LineNumber { get; set; }
        public int ColumnNumber { get; set; }
        public DateTime DiscoveredDate { get; set; }
        public bool IsValid { get; set; }
        
        // Navigation properties
        public FileItem SourceFile { get; set; } = null!;
        public FileItem TargetFile { get; set; } = null!;
    }
    
    /// <summary>
    /// Types of file references
    /// </summary>
    public enum ReferenceType
    {
        Unknown = 0,
        Import = 1,
        Include = 2,
        Using = 3,
        Require = 4,
        Reference = 5,
        Link = 6,
        Dependency = 7,
        Script = 8,
        Style = 9,
        Image = 10,
        Data = 11,
        Configuration = 12
    }
}