using VibePruner.Core.Models;

namespace VibePruner.Core.Interfaces
{
    /// <summary>
    /// Interface for AI provider operations
    /// </summary>
    public interface IAIProvider
    {
        /// <summary>
        /// Gets the provider name
        /// </summary>
        string ProviderName { get; }
        
        /// <summary>
        /// Analyzes documentation content for consolidation
        /// </summary>
        Task<DocumentationAnalysis> AnalyzeDocumentationAsync(
            string content, 
            DocumentationType documentationType,
            CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Suggests consolidation for multiple documents
        /// </summary>
        Task<ConsolidationSuggestion> SuggestConsolidationAsync(
            IEnumerable<DocumentContent> documents,
            CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Generates a summary of file content
        /// </summary>
        Task<string> GenerateSummaryAsync(
            string content,
            int maxTokens = 500,
            CancellationToken cancellationToken = default);
        
        /// <summary>
        /// Counts tokens in content
        /// </summary>
        Task<int> CountTokensAsync(string content);
        
        /// <summary>
        /// Optimizes content for token usage
        /// </summary>
        Task<string> OptimizeContentForTokensAsync(
            string content,
            int maxTokens,
            CancellationToken cancellationToken = default);
    }
}