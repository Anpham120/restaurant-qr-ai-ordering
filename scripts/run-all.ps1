param(
    [switch]$Docker,
    [switch]$Install,
    [string]$EnvFile = "deploy/env/staging.env"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Import-DotEnv([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) { continue }
        $parts = $trimmed.Split("=", 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

if ($Docker) {
    $resolvedEnv = Join-Path $root $EnvFile
    if (-not (Test-Path -LiteralPath $resolvedEnv)) {
        throw "Missing $EnvFile. Copy a deploy/env/*.example.env file and fill required secrets first."
    }
    & docker compose --env-file $resolvedEnv -f (Join-Path $root "deploy/docker-compose.yml") up --build
    exit $LASTEXITCODE
}

Import-DotEnv (Join-Path $root "backend/.env")
Import-DotEnv (Join-Path $root "ai/.env")
Import-DotEnv (Join-Path $root "frontend/.env")

if (-not $env:Jwt__SigningKey -and $env:JWT_SIGNING_KEY) { $env:Jwt__SigningKey = $env:JWT_SIGNING_KEY }
if (-not $env:CORS_ALLOWED_ORIGINS) {
    $env:CORS_ALLOWED_ORIGINS = "http://localhost:5173;http://localhost:5174;http://localhost:5175;http://localhost:5176"
}
if (-not $env:ConnectionStrings__DefaultConnection -and $env:DB_PASSWORD) {
    $hostName = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
    $port = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
    $database = if ($env:DB_NAME) { $env:DB_NAME } else { "restaurant_qr" }
    $username = if ($env:DB_USERNAME) { $env:DB_USERNAME } else { "restaurant_user" }
    $env:ConnectionStrings__DefaultConnection = "Host=$hostName;Port=$port;Database=$database;Username=$username;Password=$($env:DB_PASSWORD)"
}

if (-not $env:Jwt__SigningKey -or $env:Jwt__SigningKey.Length -lt 32) {
    throw "Set Jwt__SigningKey in backend/.env with at least 32 random characters."
}

if ($Install -or -not (Test-Path (Join-Path $root "frontend/node_modules"))) {
    & npm.cmd ci --prefix (Join-Path $root "frontend")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & python -m pip install -r (Join-Path $root "ai/requirements.txt")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$processes = @()
try {
    $processes += Start-Process dotnet -ArgumentList @("run", "--project", (Join-Path $root "backend/src/RestaurantQrAiOrdering.Api/RestaurantQrAiOrdering.Api.csproj")) -WorkingDirectory $root -NoNewWindow -PassThru
    $processes += Start-Process python -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8001") -WorkingDirectory (Join-Path $root "ai") -NoNewWindow -PassThru
    foreach ($portal in @("customer", "admin", "kitchen", "staff")) {
        $processes += Start-Process npm.cmd -ArgumentList @("run", "dev:$portal") -WorkingDirectory (Join-Path $root "frontend") -NoNewWindow -PassThru
    }

    Write-Host "API, AI, customer, admin, kitchen and staff servers started. Press Ctrl+C to stop."
    while ($true) {
        Start-Sleep -Seconds 1
        $failed = $processes | Where-Object { $_.HasExited }
        if ($failed) { throw "A server process exited unexpectedly with code $($failed[0].ExitCode)." }
    }
}
finally {
    foreach ($process in $processes) {
        if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
    }
}
