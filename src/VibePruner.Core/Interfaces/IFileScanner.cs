using VibePruner.Core.Models;

namespace VibePruner.Core.Interfaces
{
    /// <summary>
    /// Interface for file scanning operations
    /// </summary>
    public interface IFileScanner
    {
        /// <summary>
        /// Scans a directory recursively for files
        /// </summary>
        Task<IEnumerable<FileItem>> ScanDirectoryAsync(
            string directoryPath, 
            IProgress<ScanProgress>? progress = null,
            CancellationToken cancellationToken = default);
    }
    
    /// <summary>
    /// Interface for detecting file types
    /// </summary>
    public interface IFileTypeDetector
    {
        /// <summary>
        /// Detects the type of a file based on its extension and content
        /// </summary>
        FileType DetectFileType(string filePath);
    }
}