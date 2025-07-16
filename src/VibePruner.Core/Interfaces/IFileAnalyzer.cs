using VibePruner.Core.Models;

namespace VibePruner.Core.Interfaces
{
    /// <summary>
    /// Interface for file analysis operations
    /// </summary>
    public interface IFileAnalyzer
    {
        /// <summary>
        /// Analyzes a directory and all its files
        /// </summary>
        Task<AnalysisReport> AnalyzeDirectoryAsync(string directoryPath, CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Analyzes a single file
        /// </summary>
        Task<FileAnalysisResult> AnalyzeFileAsync(string filePath, CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Extracts references from a file
        /// </summary>
        Task<IEnumerable<FileReference>> ExtractReferencesAsync(FileItem file, CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Determines if a file is orphaned (no incoming references)
        /// </summary>
        Task<bool> IsFileOrphanedAsync(Guid fileId, CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Gets the dependency graph for analysis
        /// </summary>
        Task<DependencyGraph> GetDependencyGraphAsync(string rootPath, CancellationToken cancellationToken = default);
    }
}