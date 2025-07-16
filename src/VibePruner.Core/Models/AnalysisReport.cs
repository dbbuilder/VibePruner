namespace VibePruner.Core.Models
{
    /// <summary>
    /// Represents an analysis report for a directory
    /// </summary>
    public class AnalysisReport
    {
        public Guid Id { get; set; }
        public string RootPath { get; set; } = string.Empty;
        public DateTime StartTime { get; set; }
        public DateTime EndTime { get; set; }
        public int TotalFiles { get; set; }
        public int OrphanedFiles { get; set; }
        public int ProtectedFiles { get; set; }
        public long TotalSizeInBytes { get; set; }
        public Dictionary<FileType, int> FileTypeCounts { get; set; } = new();
        public List<FileItem> Files { get; set; } = new();
        public List<string> Errors { get; set; } = new();
        public DependencyGraph? DependencyGraph { get; set; }
    }
    
    /// <summary>
    /// Represents a dependency graph
    /// </summary>
    public class DependencyGraph
    {
        public Dictionary<Guid, FileItem> Nodes { get; set; } = new();
        public List<FileReference> Edges { get; set; } = new();
        
        public void AddNode(FileItem file)
        {
            if (!Nodes.ContainsKey(file.Id))
            {
                Nodes[file.Id] = file;
            }
        }
        
        public void AddEdge(FileReference reference)
        {
            Edges.Add(reference);
        }
        
        public IEnumerable<FileItem> GetOrphanedFiles()
        {
            var filesWithIncomingReferences = Edges.Select(e => e.TargetFileId).Distinct();
            return Nodes.Values.Where(f => !filesWithIncomingReferences.Contains(f.Id) && !f.IsProtected);
        }
    }
}