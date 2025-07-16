namespace VibePruner.Core.Models
{
    /// <summary>
    /// Represents an archived file entry
    /// </summary>
    public class ArchivedFile
    {
        public Guid Id { get; set; }
        public string OriginalPath { get; set; } = string.Empty;
        public string ArchivePath { get; set; } = string.Empty;
        public DateTime ArchivedDate { get; set; }
        public string Reason { get; set; } = string.Empty;
        public long SizeInBytes { get; set; }
        public string FileHash { get; set; } = string.Empty;
        public bool IsCompressed { get; set; }
        public Guid? ArchiveSessionId { get; set; }
        
        // For restoration tracking
        public bool IsRestored { get; set; }
        public DateTime? RestoredDate { get; set; }
        public string? RestoredBy { get; set; }
    }
}