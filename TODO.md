# VibePruner Development TODO

## Autonomous Development Protocol Active

This TODO follows the Autonomous Development Protocol with TDD methodology. Each task includes test-first implementation, comprehensive error handling, and incremental commits.

## Git Management Protocol
- Commit frequency: Every 15-30 minutes or logical unit completion
- Push frequency: Every 3-4 commits or major milestone
- Commit format: `type(scope): description` (feat, fix, test, refactor, docs)
- Always check .gitignore before commits

## Current Sprint Priority

### HIGH PRIORITY - Core Infrastructure Setup

- [ ] **IMMEDIATE: Add projects to solution file** (est: 30m)
  - Run dotnet sln add for all projects in src/
  - Verify solution builds successfully
  - Git commit: `fix(solution): add all projects to solution file`

- [ ] **Setup Entity Framework Core with migrations** (est: 2h)
  - Write tests for DbContext configuration
  - Create VibePrunerDbContext with all entities
  - Configure connection string from appsettings
  - Generate initial migration
  - Test database creation and connectivity
  - Git commits: `test(ef): add DbContext configuration tests`, `feat(ef): implement DbContext and entities`, `feat(ef): add initial migration`

- [ ] **Configure Serilog structured logging** (est: 1.5h)
  - Write tests for logging configuration
  - Implement Serilog with file/console sinks
  - Add Application Insights sink
  - Create logging middleware for API
  - Test structured logging output
  - Git commits: `test(logging): add Serilog configuration tests`, `feat(logging): implement Serilog with multiple sinks`

- [ ] **Implement Azure Key Vault integration** (est: 2h)
  - Write tests for secret retrieval
  - Configure Key Vault client with DefaultAzureCredential
  - Implement IConfiguration extension for Key Vault
  - Add retry policies with Polly
  - Test local development with Azure CLI auth
  - Git commits: `test(keyvault): add secret management tests`, `feat(keyvault): implement Azure Key Vault provider`

### MEDIUM PRIORITY - Core Business Logic

- [ ] **Implement file scanning engine** (est: 4h)
  - Write comprehensive tests for FileScanner
  - Handle multiple file systems (local, network, cloud)
  - Implement parallel scanning with cancellation
  - Add progress reporting
  - Test with large directory structures
  - Git commits: `test(scanner): add file scanning tests`, `feat(scanner): implement parallel file scanning`, `feat(scanner): add progress reporting`

- [ ] **Build file type detection system** (est: 3h)
  - Write tests for file type identification
  - Implement content-based detection
  - Add programming language detection
  - Create file categorization rules
  - Test with various file types
  - Git commits: `test(filetype): add file type detection tests`, `feat(filetype): implement content-based detection`

- [ ] **Create dependency analysis engine** (est: 6h)
  - Write tests for dependency tracking
  - Parse import/include statements for major languages
  - Build dependency graph
  - Implement circular dependency detection
  - Test with real codebases
  - Git commits: `test(deps): add dependency analysis tests`, `feat(deps): implement language parsers`, `feat(deps): add dependency graph builder`

### Docker Infrastructure Setup

- [ ] **Setup Docker development environment** (est: 3h)
  - Create docker-compose.yml with project isolation
  - Configure SQL Server container with port 14333
  - Setup volume for database persistence
  - Create .env.docker with COMPOSE_PROJECT_NAME=vibepruner
  - Configure network with subnet 172.25.0.0/16
  - Add npm scripts: docker:up, docker:down, docker:clean
  - Create DOCKER.md documentation
  - Git commits: `feat(docker): add isolated Docker environment`, `docs(docker): add Docker setup documentation`

### Test Infrastructure

- [ ] **Setup unit test project structure** (est: 2h)
  - Create VibePruner.Tests.Unit project
  - Configure xUnit with test runners
  - Add FluentAssertions for better test readability
  - Setup Moq for mocking
  - Create test data builders
  - Git commits: `test(infra): setup unit test project`, `test(infra): add test utilities and builders`

- [ ] **Setup integration test infrastructure** (est: 3h)
  - Create VibePruner.Tests.Integration project
  - Configure TestContainers for SQL Server
  - Setup WebApplicationFactory for API tests
  - Create test database seeding
  - Add test file system helpers
  - Git commits: `test(infra): setup integration test project`, `test(infra): add TestContainers configuration`

### AI Provider Integration

- [ ] **Implement Claude AI provider** (est: 4h)
  - Write tests for Claude API integration
  - Implement retry logic with exponential backoff
  - Add token counting and limits
  - Create prompt templates
  - Test with actual API (use test key)
  - Git commits: `test(ai): add Claude provider tests`, `feat(ai): implement Claude AI provider with retry`

- [ ] **Implement OpenAI provider** (est: 3h)
  - Write tests for OpenAI integration
  - Implement GPT-4 support
  - Add streaming response handling
  - Test token limits and pricing
  - Git commits: `test(ai): add OpenAI provider tests`, `feat(ai): implement OpenAI provider`

- [ ] **Create AI provider factory** (est: 2h)
  - Write tests for provider selection
  - Implement factory pattern
  - Add fallback logic between providers
  - Test provider switching
  - Git commits: `test(ai): add provider factory tests`, `feat(ai): implement AI provider factory`

### CLI Implementation

- [ ] **Setup command-line parser** (est: 2h)
  - Write tests for command parsing
  - Implement with System.CommandLine
  - Add command validation
  - Create help documentation
  - Test all command scenarios
  - Git commits: `test(cli): add command parser tests`, `feat(cli): implement command-line interface`

- [ ] **Implement analyze command** (est: 4h)
  - Write tests for analysis workflow
  - Wire up file scanner and analyzer
  - Add progress reporting
  - Implement result formatting
  - Test with sample projects
  - Git commits: `test(cli): add analyze command tests`, `feat(cli): implement analyze command`

### API Implementation

- [ ] **Setup API project with Swagger** (est: 2h)
  - Configure minimal APIs
  - Add Swagger/OpenAPI documentation
  - Setup CORS policies
  - Add health checks
  - Test API startup
  - Git commits: `feat(api): setup minimal API with Swagger`, `feat(api): add health checks`

- [ ] **Implement analysis endpoints** (est: 3h)
  - Write tests for API endpoints
  - Create POST /analyze endpoint
  - Add GET /analysis/{id} endpoint
  - Implement background job processing
  - Test with integration tests
  - Git commits: `test(api): add analysis endpoint tests`, `feat(api): implement analysis endpoints`

### Data Persistence

- [ ] **Implement repository pattern** (est: 3h)
  - Write tests for repositories
  - Create generic repository base
  - Implement specific repositories
  - Add unit of work pattern
  - Test CRUD operations
  - Git commits: `test(data): add repository tests`, `feat(data): implement repository pattern`

- [ ] **Create stored procedures** (est: 2h)
  - Write procedures for complex queries
  - Add performance indexes
  - Create views for reporting
  - Test query performance
  - Git commits: `feat(db): add stored procedures and indexes`

### LOW PRIORITY - Enhancement Features

- [ ] **Add caching layer** (est: 2h)
  - Implement in-memory caching
  - Add Redis support
  - Cache file analysis results
  - Test cache invalidation

- [ ] **Create notification system** (est: 3h)
  - Email notifications for long-running tasks
  - Webhook support for CI/CD integration
  - Real-time updates via SignalR

- [ ] **Build reporting dashboard** (est: 4h)
  - Create Blazor/React dashboard
  - Show analysis visualizations
  - Export reports to PDF/Excel

## Completed Tasks

### Initial Setup - [COMPLETED]
- [x] COMPLETED: Initialize Git repository - 2025-01-16
- [x] COMPLETED: Create initial project structure - 2025-01-16
- [x] COMPLETED: Setup initial documentation - 2025-01-16
- [x] COMPLETED: Add all projects to solution file - 2025-01-16
- [x] COMPLETED: Design AI-assisted file validation system - 2025-01-16

## Blockers and Dependencies

- [ ] BLOCKED: Azure Key Vault testing - Need Azure subscription or emulator
- [ ] BLOCKED: AI provider testing - Need API keys in Key Vault

## Technical Debt and Refactoring

- [ ] Refactor VibePruner.Core duplicate directory structure
- [ ] Update all file permissions (remove execute bit from non-scripts)
- [ ] Add .editorconfig for consistent code style
- [ ] Create Directory.Build.props for shared build settings

## Documentation Updates

- [ ] Update README with actual CLI commands after implementation
- [ ] Create API documentation with examples
- [ ] Add architecture diagrams
- [ ] Write deployment guide for Azure

## Performance and Optimization

- [ ] Profile file scanning for large directories
- [ ] Optimize dependency graph algorithms
- [ ] Add database query optimization
- [ ] Implement lazy loading for large results

## Security Hardening

- [ ] Add input validation for all user inputs
- [ ] Implement rate limiting for API
- [ ] Add authentication/authorization
- [ ] Security audit for file system access

## Testing Coverage Goals

- [ ] Achieve 80% code coverage for Core project
- [ ] Full integration test coverage for API endpoints
- [ ] End-to-end tests for CLI commands
- [ ] Performance benchmarks for file scanning

## Notes for Autonomous Execution

1. **Always start with tests** - Write failing tests before implementation
2. **Commit frequently** - Use descriptive commit messages
3. **Update .gitignore** - Check for new patterns before each commit
4. **Handle errors gracefully** - Never let the application crash
5. **Log everything important** - Use structured logging with context
6. **Document complex logic** - Future developers will thank you
7. **Check TODO after each task** - Mark completed, add discovered tasks

## Git Commit Guidelines

```bash
# After writing tests
git add . && git commit -m "test(scope): add tests for feature"

# After implementation
git add . && git commit -m "feat(scope): implement feature"

# After refactoring
git add . && git commit -m "refactor(scope): improve code quality"

# After fixing bugs
git add . && git commit -m "fix(scope): resolve issue description"

# After documentation
git add . && git commit -m "docs(scope): update documentation"
```

## Execution Order

1. Fix solution file (add all projects)
2. Setup Entity Framework with migrations
3. Configure logging and Azure Key Vault
4. Implement file scanning engine
5. Build test infrastructure
6. Continue with business logic implementation

Remember: "Progress over perfection" - Keep moving forward with well-tested, documented code.