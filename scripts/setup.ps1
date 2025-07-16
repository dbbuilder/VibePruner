# VibePruner Setup Script - Windows PowerShell

# Create directory structure
Write-Host "Creating project directories..." -ForegroundColor Green
$directories = @(
    "D:\dev2\VibePruner\src\VibePruner.Core"
    "D:\dev2\VibePruner\src\VibePruner.Infrastructure" 
    "D:\dev2\VibePruner\src\VibePruner.Application"
    "D:\dev2\VibePruner\src\VibePruner.CLI"
    "D:\dev2\VibePruner\src\VibePruner.API"
    "D:\dev2\VibePruner\tests\VibePruner.Core.Tests"
    "D:\dev2\VibePruner\tests\VibePruner.Infrastructure.Tests"
    "D:\dev2\VibePruner\tests\VibePruner.Application.Tests"
    "D:\dev2\VibePruner\database\StoredProcedures"
    "D:\dev2\VibePruner\database\Tables"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created: $dir" -ForegroundColor Yellow
    }
}

# Create projects
Write-Host "`nCreating .NET projects..." -ForegroundColor Green
Set-Location "D:\dev2\VibePruner"

# Create solution if not exists
if (!(Test-Path "VibePruner.sln")) {
    dotnet new sln -n VibePruner
}

# Create Core project
Set-Location "src\VibePruner.Core"
dotnet new classlib -f net8.0 --force
Set-Location "..\.."

# Create Infrastructure project  
Set-Location "src\VibePruner.Infrastructure"
dotnet new classlib -f net8.0 --force
Set-Location "..\.."

# Create Application project
Set-Location "src\VibePruner.Application"
dotnet new classlib -f net8.0 --force
Set-Location "..\.."

# Create CLI project
Set-Location "src\VibePruner.CLI"
dotnet new console -f net8.0 --force
Set-Location "..\.."

# Create API project
Set-Location "src\VibePruner.API"
dotnet new webapi -f net8.0 --force
Set-Location "..\.."

# Add projects to solution
Write-Host "`nAdding projects to solution..." -ForegroundColor Green
dotnet sln add src\VibePruner.Core\VibePruner.Core.csproj
dotnet sln add src\VibePruner.Infrastructure\VibePruner.Infrastructure.csproj
dotnet sln add src\VibePruner.Application\VibePruner.Application.csproj
dotnet sln add src\VibePruner.CLI\VibePruner.CLI.csproj
dotnet sln add src\VibePruner.API\VibePruner.API.csproj

Write-Host "`nSetup completed!" -ForegroundColor Green