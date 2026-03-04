# Complete Setup Script for NBFC Loan Platform
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NBFC Loan Platform - Complete Setup  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker Desktop
Write-Host "Step 1: Checking Docker Desktop..." -ForegroundColor Yellow
$dockerService = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue

if ($null -eq $dockerService) {
    Write-Host "❌ Docker Desktop not installed!" -ForegroundColor Red
    Write-Host "   Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

if ($dockerService.Status -ne "Running") {
    Write-Host "⚠️  Docker Desktop is not running!" -ForegroundColor Yellow
    Write-Host "   Starting Docker Desktop..." -ForegroundColor Cyan
    Start-Service "com.docker.service"
    Write-Host "   Waiting for Docker Desktop to initialize (30 seconds)..." -ForegroundColor Cyan
    Start-Sleep -Seconds 30
} else {
    Write-Host "✅ Docker Desktop is running" -ForegroundColor Green
}

# Step 2: Navigate to project directory
Write-Host ""
Write-Host "Step 2: Navigating to project directory..." -ForegroundColor Yellow
cd c:\Users\KIIT0001\Downloads\bank-agent
Write-Host "✅ Current directory: $(Get-Location)" -ForegroundColor Green

# Step 3: Check .env file
Write-Host ""
Write-Host "Step 3: Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path "backend\.env") {
    Write-Host "✅ .env file exists" -ForegroundColor Green
    
    # Check critical variables
    $envContent = Get-Content "backend\.env" -Raw
    
    if ($envContent -match "OPENAI_API_KEY=your-openai-api-key-here") {
        Write-Host "⚠️  OpenAI API key not configured!" -ForegroundColor Yellow
        Write-Host "   Please update OPENAI_API_KEY in backend\.env" -ForegroundColor Yellow
        Write-Host "   The system will work but LangGraph workflow needs OpenAI" -ForegroundColor Cyan
    }
    
    if ($envContent -match "ENCRYPTION_KEY=your-fernet") {
        Write-Host "⚠️  Encryption key not configured!" -ForegroundColor Yellow
        Write-Host "   Generating encryption key..." -ForegroundColor Cyan
        
        # Generate Fernet key
        cd backend
        $key = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
        
        if ($key) {
            (Get-Content ".env") -replace "ENCRYPTION_KEY=your-fernet-encryption-key-here-32-bytes-base64-encoded", "ENCRYPTION_KEY=$key" | Set-Content ".env"
            Write-Host "✅ Encryption key generated and saved" -ForegroundColor Green
        }
        
        cd ..
    }
} else {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    exit 1
}

# Step 4: Start infrastructure services
Write-Host ""
Write-Host "Step 4: Starting infrastructure services (MongoDB, Redis)..." -ForegroundColor Yellow
docker-compose up -d mongodb redis

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Infrastructure services started" -ForegroundColor Green
    Write-Host "   Waiting for services to initialize (15 seconds)..." -ForegroundColor Cyan
    Start-Sleep -Seconds 15
} else {
    Write-Host "❌ Failed to start services!" -ForegroundColor Red
    Write-Host "   Try running Docker Desktop manually first" -ForegroundColor Yellow
    exit 1
}

# Step 5: Check services status
Write-Host ""
Write-Host "Step 5: Verifying services..." -ForegroundColor Yellow
docker-compose ps
Write-Host ""

# Step 6: Setup Python environment
Write-Host "Step 6: Setting up Python environment..." -ForegroundColor Yellow
cd backend

if (!(Test-Path "venv")) {
    Write-Host "   Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
}

Write-Host "   Activating virtual environment..." -ForegroundColor Cyan
.\venv\Scripts\Activate.ps1

Write-Host "   Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some dependencies may have installation issues" -ForegroundColor Yellow
}

# Step 7: Generate mock data
Write-Host ""
Write-Host "Step 7: Generating mock data (1000 records)..." -ForegroundColor Yellow

if (!(Test-Path "mock_data\generated")) {
    New-Item -ItemType Directory -Path "mock_data\generated" -Force | Out-Null
}

python mock_data\generator.py --records 1000 --output mock_data\generated

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Mock data generated" -ForegroundColor Green
} else {
    Write-Host "⚠️  Mock data generation had issues, will generate on-the-fly" -ForegroundColor Yellow
}

# Step 8: Start backend server
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "         SETUP COMPLETE! 🚀            " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Make sure you've added your OpenAI API key to backend\.env" -ForegroundColor White
Write-Host "2. Start the backend server:" -ForegroundColor White
Write-Host "   cd backend" -ForegroundColor Cyan
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   python main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Access the application:" -ForegroundColor White
Write-Host "   - API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   - Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "   - Health: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Run tests with QUICKSTART.md examples" -ForegroundColor White
Write-Host ""
Write-Host "Services Status:" -ForegroundColor Yellow
docker-compose ps
Write-Host ""

# Ask if user wants to start backend now
$response = Read-Host "Do you want to start the backend server now? (Y/N)"
if ($response -eq "Y" -or $response -eq "y") {
    Write-Host ""
    Write-Host "Starting backend server..." -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
    Write-Host ""
    python main.py
}
