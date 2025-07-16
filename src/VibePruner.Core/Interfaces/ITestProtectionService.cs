using VibePruner.Core.Models;

namespace VibePruner.Core.Interfaces
{
    /// <summary>
    /// Interface for test protection and validation
    /// </summary>
    public interface ITestProtectionService
    {
        /// <summary>
        /// Discovers and catalogs all tests in the project
        /// </summary>
        Task<TestManifest> DiscoverTestsAsync(string projectPath, CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Executes tests to establish baseline
        /// </summary>
        Task<TestExecutionResult> ExecuteTestsAsync(TestManifest manifest, CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Validates that tests still work after file operations
        /// </summary>
        Task<ValidationResult> ValidateTestIntegrityAsync(TestManifest manifest, CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Identifies files critical for test execution
        /// </summary>
        Task<IEnumerable<string>> GetTestCriticalFilesAsync(string projectPath, CancellationToken cancellationToken = default);
    }
    
    /// <summary>
    /// Interface for analyzing markdown file references
    /// </summary>
    public interface IMarkdownReferenceAnalyzer
    {
        /// <summary>
        /// Analyzes markdown files for file references and importance indicators
        /// </summary>
        Task<MarkdownAnalysisResult> AnalyzeMarkdownFilesAsync(string projectPath, CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Extracts file references from a markdown file
        /// </summary>
        Task<IEnumerable<FileReference>> ExtractFileReferencesAsync(string markdownPath, CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Determines if a file is marked as temporary or deprecated in documentation
        /// </summary>
        Task<FileImportanceInfo> GetFileImportanceAsync(string filePath, IEnumerable<string> markdownPaths, CancellationToken cancellationToken = default);
    }
}