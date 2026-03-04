# Simple API Status Checker
Write-Host "Backend API Status Check" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

# Check health
Write-Host "`nChecking /health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health"
    Write-Host "✅ Health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed" -ForegroundColor Red
}

# Check OpenAPI spec
Write-Host "`nChecking /openapi.json..." -ForegroundColor Yellow
try {
    $openapi = Invoke-RestMethod -Uri "http://localhost:8000/openapi.json"
    Write-Host "✅ OpenAPI Version: $($openapi.openapi)" -ForegroundColor Green
    Write-Host "`nAvailable endpoints:" -ForegroundColor Cyan
    foreach ($path in $openapi.paths.PSObject.Properties.Name | Sort-Object) {
        Write-Host "  $path" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Failed" -ForegroundColor Red
}
