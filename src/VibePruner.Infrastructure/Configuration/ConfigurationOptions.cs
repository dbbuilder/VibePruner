namespace VibePruner.Infrastructure.Configuration
{
    /// <summary>
    /// Configuration options for file analysis
    /// </summary>
    public class FileAnalysisOptions
    {
        public int MaxFileSizeInMB { get; set; } = 100;
        public int MaxFileSizeForHashingInMB { get; set; } = 50;
        public int ParallelismDegree { get; set; } = 4;
        public List<string> ProtectedFilePatterns { get; set; } = new();
        public TokenOptimizationOptions TokenOptimization { get; set; } = new();
    }
    
    /// <summary>
    /// Token optimization options
    /// </summary>
    public class TokenOptimizationOptions
    {
        public int MaxTokensPerRequest { get; set; } = 3000;
        public int ChunkOverlapTokens { get; set; } = 200;
    }
    
    /// <summary>
    /// Archive settings configuration
    /// </summary>
    public class ArchiveSettings
    {
        public string ArchiveRootPath { get; set; } = string.Empty;
        public bool CompressionEnabled { get; set; } = true;
        public int RetentionDays { get; set; } = 90;
    }
    
    /// <summary>
    /// Cleanup rules configuration
    /// </summary>
    public class CleanupRules
    {
        public int LogFileMaxAgeInDays { get; set; } = 30;
        public List<string> TempFilePatterns { get; set; } = new();
        public List<string> TestFilePatterns { get; set; } = new();
        public int ExportFileMaxAgeInDays { get; set; } = 60;
    }
    
    /// <summary>
    /// AI provider configuration
    /// </summary>
    public class AIProviderOptions
    {
        public string ApiKey { get; set; } = string.Empty;
        public string BaseUrl { get; set; } = string.Empty;
        public string Model { get; set; } = string.Empty;
        public int MaxTokens { get; set; } = 4096;
    }
}