namespace VibePruner.Core.Models
{
    /// <summary>
    /// Represents a catalog of tests in the project
    /// </summary>
    public class TestManifest
    {
        public string ProjectPath { get; set; } = string.Empty;
        public DateTime DiscoveredDate { get; set; }
        public List<TestEntry> Tests { get; set; } = new();
        public List<string> TestRunners { get; set; } = new();
        public List<string> TestScripts { get; set; } = new();
        public Dictionary<string, string> TestCommands { get; set; } = new();
        public List<string> CriticalTestFiles { get; set; } = new();
    }
    
    /// <summary>
    /// Represents a single test or test suite
    /// </summary>
    public class TestEntry
    {
        public string Name { get; set; } = string.Empty;
        public string FilePath { get; set; } = string.Empty;
        public string TestFramework { get; set; } = string.Empty;
        public TestType Type { get; set; }
        public List<string> Dependencies { get; set; } = new();
    }
    
    /// <summary>
    /// Types of tests
    /// </summary>
    public enum TestType
    {
        Unit,
        Integration,
        E2E,
        Performance,
        Security
    }
    
    /// <summary>
    /// Result of test execution
    /// </summary>
    public class TestExecutionResult
    {
        public bool Success { get; set; }
        public int TotalTests { get; set; }
        public int PassedTests { get; set; }
        public int FailedTests { get; set; }
        public int SkippedTests { get; set; }
        public TimeSpan Duration { get; set; }
        public List<string> FailedTestNames { get; set; } = new();
        public string Output { get; set; } = string.Empty;
    }
    
    /// <summary>
    /// Result of test validation
    /// </summary>
    public class ValidationResult
    {
        public bool IsValid { get; set; }
        public List<string> BrokenTests { get; set; } = new();
        public List<string> MissingFiles { get; set; } = new();
        public List<string> Warnings { get; set; } = new();
        public string Recommendation { get; set; } = string.Empty;
    }
}