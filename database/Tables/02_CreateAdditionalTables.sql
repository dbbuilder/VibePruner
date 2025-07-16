-- Operation Logs Table
CREATE TABLE OperationLogs (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    SessionId UNIQUEIDENTIFIER NOT NULL,
    Timestamp DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    OperationType NVARCHAR(50) NOT NULL,
    FilePath NVARCHAR(500) NOT NULL,
    Action NVARCHAR(50) NOT NULL,
    Reason NVARCHAR(MAX) NOT NULL,
    UserApproved BIT NOT NULL,
    UserReason NVARCHAR(MAX) NULL,
    Success BIT NOT NULL,
    ErrorMessage NVARCHAR(MAX) NULL,
    DurationMs INT NOT NULL,
    AdditionalData NVARCHAR(MAX) NULL, -- JSON data
    CONSTRAINT FK_OperationLogs_Session FOREIGN KEY (SessionId) REFERENCES AnalysisSessions(Id),
    CONSTRAINT CK_OperationType CHECK (OperationType IN ('Scan', 'Analyze', 'Propose', 'Execute', 'Validate', 'Rollback'))
)

-- Test Manifests Table
CREATE TABLE TestManifests (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    SessionId UNIQUEIDENTIFIER NOT NULL,
    ProjectPath NVARCHAR(500) NOT NULL,
    DiscoveredDate DATETIME2 NOT NULL,
    TestData NVARCHAR(MAX) NOT NULL, -- JSON serialized TestManifest
    CONSTRAINT FK_TestManifests_Session FOREIGN KEY (SessionId) REFERENCES AnalysisSessions(Id)
)

-- Test Execution Results Table
CREATE TABLE TestExecutionResults (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    SessionId UNIQUEIDENTIFIER NOT NULL,
    ExecutionDate DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    Success BIT NOT NULL,
    TotalTests INT NOT NULL,
    PassedTests INT NOT NULL,
    FailedTests INT NOT NULL,
    SkippedTests INT NOT NULL,
    DurationMs INT NOT NULL,
    Output NVARCHAR(MAX) NULL,
    CONSTRAINT FK_TestExecution_Session FOREIGN KEY (SessionId) REFERENCES AnalysisSessions(Id)
)

-- Project Profiles Table
CREATE TABLE ProjectProfiles (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    ProjectType NVARCHAR(50) NOT NULL,
    FilePatternWeights NVARCHAR(MAX) NOT NULL, -- JSON data
    CommonlyProtectedPatterns NVARCHAR(MAX) NOT NULL, -- JSON array
    CommonlyArchivedPatterns NVARCHAR(MAX) NOT NULL, -- JSON array
    UserOverrideFrequency NVARCHAR(MAX) NOT NULL, -- JSON data
    LastUpdated DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    SessionCount INT NOT NULL DEFAULT 0
)