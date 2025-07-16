using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using VibePruner.Core.Interfaces;
using VibePruner.Core.Models;
using VibePruner.Infrastructure.Configuration;

namespace VibePruner.Infrastructure.Services
{
    /// <summary>
    /// Service for scanning and analyzing files
    /// </summary>
    public class FileScanner : IFileScanner
    {
        private readonly ILogger<FileScanner> _logger;
        private readonly FileAnalysisOptions _options;
        private readonly IFileTypeDetector _fileTypeDetector;
        
        public FileScanner(
            ILogger<FileScanner> logger,
            IOptions<FileAnalysisOptions> options,
            IFileTypeDetector fileTypeDetector)
        {
            _logger = logger;
            _options = options.Value;
            _fileTypeDetector = fileTypeDetector;
        }
        
        /// <summary>
        /// Scans a directory recursively for files
        /// </summary>
        public async Task<IEnumerable<FileItem>> ScanDirectoryAsync(
            string directoryPath, 
            IProgress<ScanProgress>? progress = null,
            CancellationToken cancellationToken = default)
        {
            _logger.LogInformation("Starting directory scan: {DirectoryPath}", directoryPath);
            
            var files = new List<FileItem>();
            var scanProgress = new ScanProgress { CurrentDirectory = directoryPath };
            
            try
            {
                await ScanDirectoryRecursiveAsync(directoryPath, files, scanProgress, progress, cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error scanning directory: {DirectoryPath}", directoryPath);
                throw;
            }
            
            _logger.LogInformation("Directory scan completed. Found {FileCount} files", files.Count);
            return files;
        }        
        private async Task ScanDirectoryRecursiveAsync(
            string directoryPath,
            List<FileItem> files,
            ScanProgress scanProgress,
            IProgress<ScanProgress>? progress,
            CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            
            var directoryInfo = new DirectoryInfo(directoryPath);
            if (!directoryInfo.Exists)
            {
                _logger.LogWarning("Directory does not exist: {DirectoryPath}", directoryPath);
                return;
            }
            
            // Update progress
            scanProgress.CurrentDirectory = directoryPath;
            scanProgress.DirectoriesScanned++;
            progress?.Report(scanProgress);
            
            // Process files in parallel
            var fileInfos = directoryInfo.GetFiles();
            var fileTasks = fileInfos.Select(fileInfo => Task.Run(async () =>
            {
                try
                {
                    var fileItem = await CreateFileItemAsync(fileInfo, directoryPath);
                    return fileItem;
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Error processing file: {FilePath}", fileInfo.FullName);
                    scanProgress.Errors.Add($"Error processing {fileInfo.FullName}: {ex.Message}");
                    return null;
                }
            }, cancellationToken));
            
            var fileItems = await Task.WhenAll(fileTasks);
            files.AddRange(fileItems.Where(f => f != null)!);
            
            scanProgress.FilesScanned += fileItems.Length;
            progress?.Report(scanProgress);
            
            // Recursively scan subdirectories
            var subdirectories = directoryInfo.GetDirectories();
            foreach (var subdirectory in subdirectories)
            {
                if (ShouldSkipDirectory(subdirectory.Name))
                {
                    _logger.LogDebug("Skipping directory: {DirectoryName}", subdirectory.Name);
                    continue;
                }
                
                await ScanDirectoryRecursiveAsync(
                    subdirectory.FullName, 
                    files, 
                    scanProgress, 
                    progress, 
                    cancellationToken);
            }
        }        
        private async Task<FileItem> CreateFileItemAsync(FileInfo fileInfo, string rootPath)
        {
            var fileItem = new FileItem
            {
                Id = Guid.NewGuid(),
                FullPath = fileInfo.FullName,
                RelativePath = Path.GetRelativePath(rootPath, fileInfo.FullName),
                FileName = fileInfo.Name,
                Extension = fileInfo.Extension,
                SizeInBytes = fileInfo.Length,
                CreatedDate = fileInfo.CreationTimeUtc,
                ModifiedDate = fileInfo.LastWriteTimeUtc,
                LastAnalyzedDate = DateTime.UtcNow,
                FileType = _fileTypeDetector.DetectFileType(fileInfo.FullName)
            };
            
            // Calculate file hash for duplicate detection
            if (fileInfo.Length < _options.MaxFileSizeForHashingInMB * 1024 * 1024)
            {
                fileItem.FileHash = await CalculateFileHashAsync(fileInfo.FullName);
            }
            
            // Check if file is protected
            fileItem.IsProtected = IsProtectedFile(fileInfo.FullName);
            
            return fileItem;
        }
        
        private async Task<string> CalculateFileHashAsync(string filePath)
        {
            using var sha256 = SHA256.Create();
            using var stream = File.OpenRead(filePath);
            var hash = await sha256.ComputeHashAsync(stream);
            return Convert.ToBase64String(hash);
        }
        
        private bool IsProtectedFile(string filePath)
        {
            var fileName = Path.GetFileName(filePath);
            return _options.ProtectedFilePatterns.Any(pattern => 
                FileMatchesPattern(fileName, pattern));
        }
        
        private bool ShouldSkipDirectory(string directoryName)
        {
            var skipPatterns = new[] { ".git", ".vs", "bin", "obj", "node_modules", ".idea", "__pycache__" };
            return skipPatterns.Contains(directoryName, StringComparer.OrdinalIgnoreCase);
        }
        
        private bool FileMatchesPattern(string fileName, string pattern)
        {
            // Simple wildcard matching
            var regexPattern = "^" + Regex.Escape(pattern).Replace("\\*", ".*") + "$";
            return Regex.IsMatch(fileName, regexPattern, RegexOptions.IgnoreCase);
        }
    }
    
    /// <summary>
    /// Progress information for file scanning
    /// </summary>
    public class ScanProgress
    {
        public string CurrentDirectory { get; set; } = string.Empty;
        public int FilesScanned { get; set; }
        public int DirectoriesScanned { get; set; }
        public List<string> Errors { get; set; } = new();
    }
}