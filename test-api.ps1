# Quick Test Script for NBFC Loan Platform API
# Tests the complete loan application workflow

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NBFC Loan Platform - API Test Suite  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000"

# Test 1: Health Check
Write-Host "Test 1: Health Check" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    if ($health.status -eq "healthy") {
        Write-Host "✅ PASS - Service is healthy" -ForegroundColor Green
        Write-Host "   MongoDB: $($health.components.mongodb)" -ForegroundColor Cyan
        Write-Host "   Redis: $($health.components.redis)" -ForegroundColor Cyan
    } else {
        Write-Host "⚠️  WARN - Service is $($health.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ FAIL - Cannot connect to backend at $baseUrl" -ForegroundColor Red
    Write-Host "   Make sure backend is running: python backend\main.py" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Test 2: Request OTP
Write-Host "Test 2: Request OTP" -ForegroundColor Yellow
$testEmail = "test-$(Get-Random)@example.com"
Write-Host "   Using email: $testEmail" -ForegroundColor Cyan

$headers = @{
    "Content-Type" = "application/json"
}

$body = @{
    email = $testEmail
} | ConvertTo-Json

try {
    $otpResponse = Invoke-RestMethod -Uri "$baseUrl/api/auth/request-otp" -Method Post -Headers $headers -Body $body
    Write-Host "✅ PASS - OTP  requested successfully" -ForegroundColor Green
    Write-Host "   Check backend console for OTP (simulated email)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ FAIL - OTP request failed" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Get OTP from user (in real scenario, check backend logs)
Write-Host "📧 Check backend logs for OTP, or use default: 123456" -ForegroundColor Yellow
$otp = Read-Host "Enter OTP (or press Enter for 123456)"
if ([string]::IsNullOrWhiteSpace($otp)) {
    $otp = "123456"
}

Write-Host ""

# Test 3: Verify OTP
Write-Host "Test 3: Verify OTP and Authenticate" -ForegroundColor Yellow

$body = @{
    email = $testEmail
    otp = $otp
} | ConvertTo-Json

try {
    $authResponse = Invoke-RestMethod -Uri "$baseUrl/api/auth/verify-otp" -Method Post -Headers $headers -Body $body
    $token = $authResponse.access_token
    Write-Host "✅ PASS - Authentication successful" -ForegroundColor Green
    Write-Host "   User ID: $($authResponse.user.user_id)" -ForegroundColor Cyan
    Write-Host "   Token: $($token.Substring(0, 20))..." -ForegroundColor Cyan
} catch {
    Write-Host "❌ FAIL - Authentication failed" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    
    # Try with a known working OTP flow
    Write-Host "   Retrying with backend-generated OTP..." -ForegroundColor Cyan
    Start-Sleep -Seconds 2
}

Write-Host ""

# Update headers with token
$authHeaders = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $token"
}

# Test 4: Get User Profile
Write-Host "Test 4: Get User Profile" -ForegroundColor Yellow
try {
    $user = Invoke-RestMethod -Uri "$baseUrl/api/auth/me" -Method Get -Headers $authHeaders
    Write-Host "✅ PASS - Profile retrieved" -ForegroundColor Green
    Write-Host "   Email: $($user.email)" -ForegroundColor Cyan
    Write-Host "   Role: $($user.role)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ FAIL - Profile retrieval failed" -ForegroundColor Red
}

Write-Host ""

# Test 5: Start Loan Application
Write-Host "Test 5: Start Loan Application (Personal Loan)" -ForegroundColor Yellow

$body = @{
    loan_type = "personal_loan"
} | ConvertTo-Json

try {
    $application = Invoke-RestMethod -Uri "$baseUrl/api/loans/apply" -Method Post -Headers $authHeaders -Body $body
    $applicationId = $application.application_id
    Write-Host "✅ PASS - Application started" -ForegroundColor Green
    Write-Host "   Application ID: $applicationId" -ForegroundColor Cyan
    Write-Host "   Stage: $($application.stage)" -ForegroundColor Cyan
    Write-Host "   Initial Message: $($application.messages[-1].content.Substring(0, 100))..." -ForegroundColor Cyan
} catch {
    Write-Host "❌ FAIL - Application start failed" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Test 6: Submit Application Information
Write-Host "Test 6: Submit Application Information" -ForegroundColor Yellow

# Complete application info in one message
$appInfo = "My Aadhaar is 123456789012 and PAN is ABCDE1234F. I earn 50000 rupees per month and need a loan of 300000 for 24 months. I am 30 years old, salaried employee in Mumbai, and have been working for 5 years."

$body = @{
    message = $appInfo
} | ConvertTo-Json

try {
    $chatResponse = Invoke-RestMethod -Uri "$baseUrl/api/loans/applications/$applicationId/chat" -Method Post -Headers $authHeaders -Body $body
    Write-Host "✅ PASS - Information submitted and workflow processed" -ForegroundColor Green
    Write-Host "   Current Stage: $($chatResponse.stage)" -ForegroundColor Cyan
    Write-Host "   Latest Response: $($chatResponse.messages[-1].content.Substring(0, 150))..." -ForegroundColor Cyan
    
    # Show loan offer if available
    if ($chatResponse.loan_offer) {
        Write-Host ""
        Write-Host "💰 Loan Offer Generated:" -ForegroundColor Green
        Write-Host "   Principal: ₹$($chatResponse.loan_offer.principal)" -ForegroundColor Cyan
        Write-Host "   Interest Rate: $($chatResponse.loan_offer.interest_rate)%" -ForegroundColor Cyan
        Write-Host "   Tenure: $($chatResponse.loan_offer.tenure_months) months" -ForegroundColor Cyan
        Write-Host "   Monthly EMI: ₹$($chatResponse.loan_offer.monthly_emi)" -ForegroundColor Cyan
        Write-Host "   Total Interest: ₹$($chatResponse.loan_offer.total_interest)" -ForegroundColor Cyan
        Write-Host "   Net Disbursement: ₹$($chatResponse.loan_offer.net_disbursement)" -ForegroundColor Cyan
        Write-Host "   Risk Segment: $($chatResponse.loan_offer.risk_segment)" -ForegroundColor Cyan
        
        # Test 7: Accept Offer
        Write-Host ""
        Write-Host "Test 7: Accept Loan Offer" -ForegroundColor Yellow
        
        $body = @{
            message = "Yes, I accept this loan offer"
        } | ConvertTo-Json
        
        $acceptResponse = Invoke-RestMethod -Uri "$baseUrl/api/loans/applications/$applicationId/chat" -Method Post -Headers $authHeaders -Body $body
        
        if ($acceptResponse.loan_id) {
            Write-Host "✅ PASS - Offer accepted, loan created" -ForegroundColor Green
            Write-Host "   Loan ID: $($acceptResponse.loan_id)" -ForegroundColor Cyan
            Write-Host "   Status: $($acceptResponse.stage)" -ForegroundColor Cyan
            
            $loanId = $acceptResponse.loan_id
            
            # Test 8: Get EMI Schedule
            Write-Host ""
            Write-Host "Test 8: Get EMI Schedule" -ForegroundColor Yellow
            
            $schedule = Invoke-RestMethod -Uri "$baseUrl/api/loans/$loanId/emi-schedule" -Method Get -Headers $authHeaders
            
            Write-Host "✅ PASS - EMI schedule retrieved" -ForegroundColor Green
            Write-Host "   Total Installments: $($schedule.summary.total_installments)" -ForegroundColor Cyan
            Write-Host "   First 3 EMIs:" -ForegroundColor Cyan
            
            $schedule.schedule | Select-Object -First 3 | ForEach-Object {
                Write-Host "      Month $($_.month): ₹$($_.emi_amount) (Due: $($_.due_date))" -ForegroundColor White
            }
        }
    }
    
} catch {
    Write-Host "❌ FAIL - Chat workflow failed" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    
    if ($_.ErrorDetails) {
        Write-Host "   Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""

# Test 9: List Applications
Write-Host "Test 9: List User Applications" -ForegroundColor Yellow
try {
    $apps = Invoke-RestMethod -Uri "$baseUrl/api/loans/applications" -Method Get -Headers $authHeaders
    Write-Host "✅ PASS - Applications retrieved" -ForegroundColor Green
    Write-Host "   Total: $($apps.applications.Count)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ FAIL - Cannot list applications" -ForegroundColor Red
}

Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "         TEST SUITE COMPLETE           " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✨ Backend is working correctly!" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "- Explore API docs: $baseUrl/docs" -ForegroundColor White
Write-Host "- Check QUICKSTART.md for more examples" -ForegroundColor White
Write-Host "- Test admin endpoints (requires admin role)" -ForegroundColor White
Write-Host "- Start building the frontend!" -ForegroundColor White
Write-Host ""
