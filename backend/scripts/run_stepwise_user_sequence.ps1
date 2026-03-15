$ErrorActionPreference = 'Stop'
Set-Location "c:/Users/KIIT0001/Downloads/bank-agent/backend"

$email = "stepwise.userseq@example.com"
$headers = @{ "Content-Type" = "application/json" }

$otpReqBody = @{ email = $email } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/request-otp" -Method Post -Headers $headers -Body $otpReqBody | Out-Null
Start-Sleep -Milliseconds 700

$otpLine = Get-Content "logs/app.log" -Tail 300 | Select-String -Pattern "Your OTP is:" | Select-Object -Last 1
if (-not $otpLine) { throw "OTP line not found in logs" }
$otpMatch = [regex]::Match($otpLine.Line, "Your OTP is:\s*(\d{6})")
if (-not $otpMatch.Success) { throw "Failed to parse OTP from log line" }
$otp = $otpMatch.Groups[1].Value

$verifyBody = @{ email = $email; otp = $otp } | ConvertTo-Json
$verifyResp = Invoke-RestMethod -Uri "http://localhost:8000/api/verify-otp" -Method Post -Headers $headers -Body $verifyBody
$token = $verifyResp.access_token
if (-not $token) { throw "No access token returned" }
$authHeaders = @{ "Content-Type" = "application/json"; "Authorization" = "Bearer $token" }

$applyBody = @{ loan_type = "personal_loan" } | ConvertTo-Json
$applyResp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/apply" -Method Post -Headers $authHeaders -Body $applyBody
$appId = $applyResp.application_id
if (-not $appId) { throw "No application_id returned" }

Write-Output "=== USER SEQUENCE TEST START ==="
Write-Output ("application_id: " + $appId)
Write-Output ("initial_stage: " + $applyResp.stage)
Write-Output ("initial_status: " + $applyResp.status)
Write-Output ("initial_assistant: " + $applyResp.messages[-1].content)

$messages = @(
    "123456789012",
    "AAAAA9999A",
    "50000",
    "salaried",
    "10yrs",
    "32",
    "tier2 city, 40 moths, 100000",
    "yes"
)

$step = 1
foreach ($msg in $messages) {
    $chatBody = @{ message = $msg } | ConvertTo-Json
    $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId/chat" -Method Post -Headers $authHeaders -Body $chatBody
    $lastAssistant = $resp.messages[-1].content

    Write-Output ""
    Write-Output ("Step " + $step + " user: " + $msg)
    Write-Output ("Stage: " + $resp.stage)
    Write-Output ("Status: " + $resp.status)
    Write-Output ("Assistant: " + $lastAssistant)

    $step++
}

Write-Output ""
Write-Output "=== USER SEQUENCE TEST END ==="
