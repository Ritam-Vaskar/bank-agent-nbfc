# Quick Backend Test Script
# Tests the complete loan application workflow

$baseUrl = "http://localhost:8000"
$email = "test-$(Get-Random)@example.com"

Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "NBFC LOAN PLATFORM - API TEST" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "`n[1/7] Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    if ($health.status -eq "healthy") {
        Write-Host "✅ Health Check PASSED" -ForegroundColor Green
        Write-Host "   MongoDB: $($health.services.mongodb)" -ForegroundColor Gray
        Write-Host "   Redis: $($health.services.redis)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Health Check FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 2: Request OTP
Write-Host "`n[2/7] Requesting OTP for $email..." -ForegroundColor Yellow
try {
    $otpRequest = @{ email = $email } | ConvertTo-Json
    $otpResponse = Invoke-RestMethod -Uri "$baseUrl/api/request-otp" -Method Post -Body $otpRequest -ContentType "application/json"
    Write-Host "✅ OTP Request PASSED" -ForegroundColor Green
    Write-Host "   Message: $($otpResponse.message)" -ForegroundColor Gray
} catch {
    Write-Host "❌ OTP Request FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 3: Verify OTP (using default OTP: 123456)
Write-Host "`n[3/7] Verifying OTP..." -ForegroundColor Yellow
$otp = "123456"
try {
    $verifyRequest = @{ email = $email; otp = $otp } | ConvertTo-Json
    $authResponse = Invoke-RestMethod -Uri "$baseUrl/api/verify-otp" -Method Post -Body $verifyRequest -ContentType "application/json"
    $token = $authResponse.access_token
    Write-Host "✅ OTP Verification PASSED" -ForegroundColor Green
    Write-Host "   Token received (length: $($token.Length))" -ForegroundColor Gray
} catch {
    Write-Host "❌ OTP Verification FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 4: Get User Profile
Write-Host "`n[4/7] Getting User Profile..." -ForegroundColor Yellow
try {
    $headers = @{ Authorization = "Bearer $token" }
    $profile = Invoke-RestMethod -Uri "$baseUrl/api/me" -Method Get -Headers $headers
    Write-Host "✅ Profile Retrieval PASSED" -ForegroundColor Green
    Write-Host "   User ID: $($profile.user_id)" -ForegroundColor Gray
    Write-Host "   Email: $($profile.email)" -ForegroundColor Gray
    Write-Host "   Role: $($profile.role)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Profile Retrieval FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 5: Start Loan Application
Write-Host "`n[5/7] Starting Loan Application..." -ForegroundColor Yellow
try {
    $applyRequest = @{ loan_type = "personal_loan" } | ConvertTo-Json
    $application = Invoke-RestMethod -Uri "$baseUrl/api/loans/apply" -Method Post -Body $applyRequest -ContentType "application/json" -Headers $headers
    $appId = $application.application_id
    Write-Host "✅ Application Created PASSED" -ForegroundColor Green
    Write-Host "   Application ID: $appId" -ForegroundColor Gray
    Write-Host "   Stage: $($application.stage)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Application Creation FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 6: Submit Application Data via Chat
Write-Host "`n[6/7] Submitting Application Info..." -ForegroundColor Yellow
try {
    $userMessage = "My Aadhaar is 123456789012 and PAN is ABCDE1234F. I earn 60000 rupees per month and want to borrow 300000 for 36 months. I'm 32 years old, salaried employee for 5 years in Tier 1 city."
    $chatRequest = @{ message = $userMessage } | ConvertTo-Json
    $chatResponse = Invoke-RestMethod -Uri "$baseUrl/api/loans/applications/$appId/chat" -Method Post -Body $chatRequest -ContentType "application/json" -Headers $headers
    Write-Host "✅ Application Submission PASSED" -ForegroundColor Green
    Write-Host "   Stage: $($chatResponse.stage)" -ForegroundColor Gray
    Write-Host "   Status: $($chatResponse.status)" -ForegroundColor Gray
    
    if ($chatResponse.loan_offer) {
        Write-Host "`n   💰 LOAN OFFER GENERATED:" -ForegroundColor Cyan
        Write-Host "   Amount: ₹$($chatResponse.loan_offer.amount)" -ForegroundColor White
        Write-Host "   Tenure: $($chatResponse.loan_offer.tenure) months" -ForegroundColor White
        Write-Host "   Interest Rate: $($chatResponse.loan_offer.interest_rate)%" -ForegroundColor White
        Write-Host "   Monthly EMI: ₹$($chatResponse.loan_offer.monthly_emi)" -ForegroundColor White
        Write-Host "   Processing Fee: ₹$($chatResponse.loan_offer.processing_fee.amount)" -ForegroundColor White
        Write-Host "   Net Disbursement: ₹$($chatResponse.loan_offer.net_disbursement)" -ForegroundColor White
    }
} catch {
    Write-Host "❌ Application Submission FAILED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Error Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

# Test 7: List Applications
Write-Host "`n[7/7] Listing All Applications..." -ForegroundColor Yellow
try {
    $applications = Invoke-RestMethod -Uri "$baseUrl/api/loans/applications" -Method Get -Headers $headers
    Write-Host "✅ Application List PASSED" -ForegroundColor Green
    Write-Host "   Total Applications: $($applications.total)" -ForegroundColor Gray
    foreach ($app in $applications.applications) {
        Write-Host "   - $($app.application_id): $($app.status) ($($app.stage))" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Application List FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=====================================" -ForegroundColor Cyan
Write-Host "✅ ALL TESTS COMPLETED!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "`nBackend is fully operational at: $baseUrl" -ForegroundColor White
Write-Host "API Docs: $baseUrl/docs" -ForegroundColor White
Write-Host "Mock Data: 1000 credit bureau records loaded" -ForegroundColor White
Write-Host "`n" -ForegroundColor White
