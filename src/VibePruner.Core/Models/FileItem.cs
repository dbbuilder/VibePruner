namespace VibePruner.Core.Models
{
    /// <summary>
    /// Represents a file in the analysis system
    /// </summary>
    public class FileItem
    {
        public Guid Id { get; set; }
        public string FullPath { get; set; } = string.Empty;
        public string RelativePath { get; set; } = string.Empty;
        public string FileName { get; set; } = string.Empty;
        public string Extension { get; set; } = string.Empty;
        public long SizeInBytes { get; set; }
        public DateTime CreatedDate { get; set; }
        public DateTime ModifiedDate { get; set; }
        public DateTime LastAnalyzedDate { get; set; }
        public string FileHash { get; set; } = string.Empty;
        public FileType FileType { get; set; }
        public bool IsProtected { get; set; }
        public bool IsOrphaned { get; set; }
        public int ReferenceCount { get; set; }
        
        // Navigation properties
        public ICollection<FileReference> OutgoingReferences { get; set; } = new List<FileReference>();
        public ICollection<FileReference> IncomingReferences { get; set; } = new List<FileReference>();
        public ICollection<FileAnalysisResult> AnalysisResults { get; set; } = new List<FileAnalysisResult>();
    }
}