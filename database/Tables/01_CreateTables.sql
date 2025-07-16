-- Create VibePruner Database
CREATE DATABASE VibePruner
GO

USE VibePruner
GO

-- Analysis Sessions Table
CREATE TABLE AnalysisSessions (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    ProjectPath NVARCHAR(500) NOT NULL,
    ProjectName NVARCHAR(255) NOT NULL,
    StartTime DATETIME2 NOT NULL,
    EndTime DATETIME2 NULL,
    Username NVARCHAR(255) NOT NULL,
    TotalFiles INT NOT NULL DEFAULT 0,
    FilesProcessed INT NOT NULL DEFAULT 0,
    Status NVARCHAR(50) NOT NULL,
    CreatedDate DATETIME2 DEFAULT GETUTCDATE(),
    CONSTRAINT CK_SessionStatus CHECK (Status IN ('InProgress', 'WaitingForApproval', 'Executing', 'Completed', 'Failed', 'RolledBack'))
)

-- File Items Table
CREATE TABLE FileItems (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    SessionId UNIQUEIDENTIFIER NOT NULL,
    FullPath NVARCHAR(500) NOT NULL,
    RelativePath NVARCHAR(500) NOT NULL,
    FileName NVARCHAR(255) NOT NULL,
    Extension NVARCHAR(50) NOT NULL,
    SizeInBytes BIGINT NOT NULL,
    CreatedDate DATETIME2 NOT NULL,
    ModifiedDate DATETIME2 NOT NULL,
    LastAnalyzedDate DATETIME2 NOT NULL,
    FileHash NVARCHAR(100) NULL,
    FileType NVARCHAR(50) NOT NULL,
    IsProtected BIT NOT NULL DEFAULT 0,
    IsOrphaned BIT NOT NULL DEFAULT 0,
    ReferenceCount INT NOT NULL DEFAULT 0,
    CONSTRAINT FK_FileItems_Session FOREIGN KEY (SessionId) REFERENCES AnalysisSessions(Id)
)

-- Proposed File Actions Table
CREATE TABLE ProposedFileActions (
    Id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    SessionId UNIQUEIDENTIFIER NOT NULL,
    FilePath NVARCHAR(500) NOT NULL,
    RelativePath NVARCHAR(500) NOT NULL,
    Action NVARCHAR(50) NOT NULL,
    Reason NVARCHAR(MAX) NOT NULL,
    ConfidenceScore FLOAT NOT NULL,
    UserApproved BIT NULL,
    UserReason NVARCHAR(MAX) NULL,
    ProposedDate DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    TargetPath NVARCHAR(500) NULL,
    CONSTRAINT FK_ProposedActions_Session FOREIGN KEY (SessionId) REFERENCES AnalysisSessions(Id),
    CONSTRAINT CK_FileAction CHECK (Action IN ('Keep', 'Archive', 'Delete', 'Consolidate', 'Move', 'Rename'))
)