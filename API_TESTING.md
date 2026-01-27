# API Testing Guide

## Quick Test Commands

### Health Checks

```bash
# Backend health
curl http://localhost:5000/health

# Agent service health
curl http://localhost:8000/health
```

### Authentication

```bash
# Sign up
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "password": "test123"
  }'

# Sign in
curl -X POST http://localhost:5000/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "demo123"
  }'
```

### Chat Flow

```bash
# Start conversation (save the accessToken from signin response)
TOKEN="your-access-token-here"

# Send first message
curl -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "I want a personal loan",
    "userId": "user123"
  }'

# Continue conversation (use loanId from response)
curl -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "5 lakhs",
    "loanId": "loan-id-from-previous-response",
    "userId": "user123"
  }'
```

### Direct Agent Testing

```bash
# Test Master Agent directly
curl -X POST http://localhost:8000/master \
  -H "Content-Type: application/json" \
  -d '{
    "loan_id": "test123",
    "user_message": "I want a personal loan of 5 lakhs for 36 months",
    "current_state": "INIT",
    "loan_data": {}
  }'

# Test with KYC
curl -X POST http://localhost:8000/master \
  -H "Content-Type: application/json" \
  -d '{
    "loan_id": "test123",
    "user_message": "ABCDE1234F",
    "current_state": "KYC",
    "loan_data": {
      "loan_type": "Personal Loan",
      "loan_amount": 500000,
      "tenure": 36
    }
  }'
```

### Mock Services

```bash
# Test CIBIL API
curl "http://localhost:8000/mock/cibil?pan=ABCDE1234F"

# Test Aadhaar API
curl "http://localhost:8000/mock/aadhaar?number=123456789012"

# Test PAN API
curl "http://localhost:8000/mock/pan?number=ABCDE1234F"
```

### Admin Endpoints

```bash
# Get all loans (admin only)
curl http://localhost:5000/api/admin/loans \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get statistics
curl http://localhost:5000/api/admin/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get audit logs
curl http://localhost:5000/api/admin/audit?loanId=loan123 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Postman Collection

Import this into Postman:

```json
{
  "info": {
    "name": "Bank Agent API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Sign Up",
          "request": {
            "method": "POST",
            "url": "http://localhost:5000/api/auth/signup",
            "body": {
              "mode": "raw",
              "raw": "{\"name\":\"Test User\",\"email\":\"test@example.com\",\"password\":\"test123\"}"
            }
          }
        },
        {
          "name": "Sign In",
          "request": {
            "method": "POST",
            "url": "http://localhost:5000/api/auth/signin",
            "body": {
              "mode": "raw",
              "raw": "{\"email\":\"demo@example.com\",\"password\":\"demo123\"}"
            }
          }
        }
      ]
    },
    {
      "name": "Chat",
      "item": [
        {
          "name": "Send Message",
          "request": {
            "method": "POST",
            "url": "http://localhost:5000/api/chat/message",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{accessToken}}"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\"message\":\"I want a personal loan\",\"userId\":\"user123\"}"
            }
          }
        }
      ]
    }
  ]
}
```

## Testing Complete Loan Flow

```bash
#!/bin/bash

# 1. Sign in
echo "Signing in..."
RESPONSE=$(curl -s -X POST http://localhost:5000/api/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"demo123"}')

TOKEN=$(echo $RESPONSE | jq -r '.accessToken')
echo "Token: $TOKEN"

# 2. Start loan application
echo -e "\n1. Starting loan application..."
RESPONSE=$(curl -s -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"I want a personal loan","userId":"user123"}')

echo $RESPONSE | jq '.'
LOAN_ID=$(echo $RESPONSE | jq -r '.loanId')

# 3. Provide amount
echo -e "\n2. Providing loan amount..."
RESPONSE=$(curl -s -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"message\":\"5 lakhs\",\"loanId\":\"$LOAN_ID\",\"userId\":\"user123\"}")

echo $RESPONSE | jq '.'

# 4. Provide tenure
echo -e "\n3. Providing tenure..."
RESPONSE=$(curl -s -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"message\":\"36 months\",\"loanId\":\"$LOAN_ID\",\"userId\":\"user123\"}")

echo $RESPONSE | jq '.'

# 5. Provide PAN
echo -e "\n4. Providing PAN..."
RESPONSE=$(curl -s -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"message\":\"ABCDE1234F\",\"loanId\":\"$LOAN_ID\",\"userId\":\"user123\"}")

echo $RESPONSE | jq '.'

# 6. Provide Aadhaar
echo -e "\n5. Providing Aadhaar..."
RESPONSE=$(curl -s -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"message\":\"123456789012\",\"loanId\":\"$LOAN_ID\",\"userId\":\"user123\"}")

echo $RESPONSE | jq '.'

# 7. Documents uploaded
echo -e "\n6. Uploading documents..."
RESPONSE=$(curl -s -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"message\":\"documents uploaded\",\"loanId\":\"$LOAN_ID\",\"userId\":\"user123\"}")

echo $RESPONSE | jq '.'

# 8. Accept offer
echo -e "\n7. Accepting offer..."
RESPONSE=$(curl -s -X POST http://localhost:5000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"message\":\"accept\",\"loanId\":\"$LOAN_ID\",\"userId\":\"user123\"}")

echo $RESPONSE | jq '.'

echo -e "\n✅ Loan application complete!"
```

Save as `test-flow.sh` and run with `bash test-flow.sh`
