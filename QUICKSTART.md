# 🚀 Quick Start Guide - NBFC Loan Platform

## Prerequisites

- **Docker Desktop** installed and running
- **Python 3.11+** installed
- **Node.js 18+** installed (for frontend, when ready)
- **Git** installed

## 🏗️ Backend Setup (Complete!)

### Step 1: Environment Setup

The `.env` file has been created. You need to:

1. **Generate Encryption Key**:
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Copy the output and update `ENCRYPTION_KEY` in `.env`

2. **Add OpenAI API Key**:
Update `OPENAI_API_KEY` in `.env` with your actual OpenAI API key (required for LangGraph LLM nodes)

### Step 2: Start Infrastructure

```powershell
# From project root
cd c:\Users\KIIT0001\Downloads\bank-agent

# Start MongoDB and Redis
docker-compose up -d mongodb redis

# Wait 10 seconds for services to initialize
Start-Sleep -Seconds 10

# Check services are running
docker-compose ps
```

### Step 3: Generate Mock Data (Optional but Recommended)

```powershell
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate 10,000 mock credit bureau records
python mock_data/generator.py --records 10000 --output mock_data/generated
```

### Step 4: Start Backend API

```powershell
# From backend directory (with venv activated)
python main.py

# OR using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Backend will be available at:**
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testing the API

### Test 1: Health Check

```powershell
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "mongodb": "connected",
    "redis": "connected"
  }
}
```

### Test 2: Request OTP (Authentication)

```powershell
$headers = @{
    "Content-Type" = "application/json"
}

$body = @{
    email = "test@example.com"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/request-otp" -Method Post -Headers $headers -Body $body

$response
```

Check console logs to see the generated OTP (simulated email).

### Test 3: Verify OTP

```powershell
$body = @{
    email = "test@example.com"
    otp = "123456"  # Replace with actual OTP from logs
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/verify-otp" -Method Post -Headers $headers -Body $body

$token = $response.access_token
$token
```

### Test 4: Start Loan Application

```powershell
$authHeaders = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $token"
}

$body = @{
    loan_type = "personal_loan"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/apply" -Method Post -Headers $authHeaders -Body $body

$applicationId = $response.application_id
$response
```

### Test 5: Chat with Workflow

```powershell
# Provide information
$body = @{
    message = "My Aadhaar is 123456789012 and PAN is ABCDE1234F. I earn 50000 per month and need a loan of 300000 for 24 months. I am 30 years old, salaried, and working in Mumbai for 5 years."
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$applicationId/chat" -Method Post -Headers $authHeaders -Body $body

$response.messages[-1].content
```

The workflow will process through:
1. ✅ KYC Verification
2. ✅ Credit Score Check
3. ✅ Policy Validation
4. ✅ Affordability Assessment
5. ✅ Risk Scoring
6. ✅ Loan Offer Generation

### Test 6: Accept Offer

```powershell
$body = @{
    message = "Yes, I accept the offer"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$applicationId/chat" -Method Post -Headers $authHeaders -Body $body

$response.loan_id
```

### Test 7: Get EMI Schedule

```powershell
$loanId = $response.loan_id

$schedule = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/$loanId/emi-schedule" -Method Get -Headers $authHeaders

$schedule.schedule | Select-Object -First 3 | Format-Table
```

### Test 8: Download Sanction Letter

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/loans/$loanId/sanction-letter" -Headers $authHeaders -OutFile "sanction_letter.pdf"

# Open the PDF
Start-Process "sanction_letter.pdf"
```

## 📊 Admin Endpoints

### Admin User Setup

By default, you need to manually create an admin user in MongoDB or update a user's role:

```javascript
// In MongoDB Compass or mongo shell
db.users.updateOne(
  { email: "admin@example.com" },
  { $set: { role: "admin" } }
)
```

### Admin Analytics

```powershell
# Login as admin first to get admin token
$adminToken = "<admin_jwt_token>"

$adminHeaders = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $adminToken"
}

# Overview Analytics
$analytics = Invoke-RestMethod -Uri "http://localhost:8000/api/admin/analytics/overview" -Method Get -Headers $adminHeaders

$analytics

# Risk Distribution
$risk = Invoke-RestMethod -Uri "http://localhost:8000/api/admin/analytics/risk-distribution" -Method Get -Headers $adminHeaders

$risk

# Audit Logs
$logs = Invoke-RestMethod -Uri "http://localhost:8000/api/admin/audit-logs" -Method Get -Headers $adminHeaders -Body "limit=10"

$logs.logs | Format-Table
```

## 🔄 Complete End-to-End Test Flow

```powershell
# Complete loan journey script
$testEmail = "borrower@test.com"

# 1. Request OTP
$otpResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/request-otp" `
    -Method Post `
    -Headers @{"Content-Type"="application/json"} `
    -Body (@{email=$testEmail} | ConvertTo-Json)

Write-Host "Check console for OTP. Enter it here:"
$otp = Read-Host

# 2. Verify OTP
$authResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/verify-otp" `
    -Method Post `
    -Headers @{"Content-Type"="application/json"} `
    -Body (@{email=$testEmail; otp=$otp} | ConvertTo-Json)

$token = $authResponse.access_token
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer $token"
}

# 3. Start Application
$app = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/apply" `
    -Method Post `
    -Headers $headers `
    -Body (@{loan_type="personal_loan"} | ConvertTo-Json)

Write-Host "`n✅ Application started: $($app.application_id)"
Write-Host "Workflow message: $($app.messages[-1].content)"

# 4. Provide information
$info = "My Aadhaar is 987654321098 and PAN is XYZAB5678C. I earn ₹60000 per month and need ₹500000 for 36 months. I'm 35 years old, salaried employee in Bangalore for 7 years."

$chat1 = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$($app.application_id)/chat" `
    -Method Post `
    -Headers $headers `
    -Body (@{message=$info} | ConvertTo-Json)

Write-Host "`n📝 Information submitted"
Write-Host "Stage: $($chat1.stage)"
Write-Host "Response: $($chat1.messages[-1].content)"

# 5. Accept offer (if reached)
if ($chat1.loan_offer) {
    Write-Host "`n💰 Loan Offer Received:"
    Write-Host "   Amount: ₹$($chat1.loan_offer.principal)"
    Write-Host "   EMI: ₹$($chat1.loan_offer.monthly_emi)"
    Write-Host "   Interest: $($chat1.loan_offer.interest_rate)%"
    
    $accept = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$($app.application_id)/chat" `
        -Method Post `
        -Headers $headers `
        -Body (@{message="Yes, I accept this offer"} | ConvertTo-Json)
    
    Write-Host "`n✅ Offer Accepted!"
    Write-Host "Loan ID: $($accept.loan_id)"
    Write-Host "Response: $($accept.messages[-1].content)"
}
```

## 📝 Logs & Monitoring

### Application Logs

```powershell
# View real-time logs
Get-Content backend\logs\app.log -Wait -Tail 50
```

### Database Inspection

```powershell
# Using MongoDB Compass
# Connect to: mongodb://localhost:27017
# Database: nbfc_loan_platform
# Collections: users, loan_applications, loans, audit_logs

# Or using mongosh
docker exec -it bank-agent-mongodb-1 mongosh

use nbfc_loan_platform
db.loan_applications.find().pretty()
db.loans.find().pretty()
db.audit_logs.find().sort({timestamp:-1}).limit(10).pretty()
```

### Redis Inspection

```powershell
docker exec -it bank-agent-redis-1 redis-cli

# View OTP keys
KEYS otp:*

# View JWT blacklist
KEYS jwt_blacklist:*

# View bureau cache
KEYS bureau_cache:*

# Get value
GET otp:test@example.com
```

## 🛠️ Troubleshooting

### MongoDB Connection Failed

```powershell
# Check if container is running
docker ps | Select-String mongodb

# Restart if needed
docker-compose restart mongodb

# Check logs
docker-compose logs mongodb
```

### Redis Connection Failed

```powershell
docker-compose restart redis
docker-compose logs redis
```

### OpenAI API Key Error

Make sure you've added your OpenAI API key to `.env`:
```
OPENAI_API_KEY=sk-...your-key-here...
```

### Import Errors

```powershell
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

## 🎯 What's Working

✅ Complete Backend API (9 modules)  
✅ LangGraph Workflow Orchestration  
✅ Authentication (OTP + JWT)  
✅ 7 Calculation Engines  
✅ Policy-Driven Underwriting  
✅ Risk-Based Pricing  
✅ PDF Sanction Letters  
✅ Audit Logging  
✅ Admin Analytics  
✅ Mock Data Generation  

## 📚 API Documentation

Once backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

All endpoints are documented with:
- Request/response schemas
- Authentication requirements
- Example payloads
- Error codes

## 🔜 Next: Frontend Development

The backend is production-ready! Next steps:
1. Initialize Next.js 14 frontend
2. Create chat interface for loan application
3. Build dashboard for active loans
4. Admin analytics UI

---

**Happy Testing! 🚀**
