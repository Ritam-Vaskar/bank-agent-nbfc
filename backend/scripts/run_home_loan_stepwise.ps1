$ErrorActionPreference = 'Stop'
Set-Location "c:/Users/KIIT0001/Downloads/bank-agent/backend"

$email = "home.stepwise.script@example.com"
$headers = @{ "Content-Type" = "application/json" }

$otpReqBody = @{ email = $email } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/request-otp" -Method Post -Headers $headers -Body $otpReqBody | Out-Null
Start-Sleep -Milliseconds 700

$otpLine = Get-Content "logs/app.log" -Tail 300 | Select-String -Pattern "Your OTP is:" | Select-Object -Last 1
$otp = [regex]::Match($otpLine.Line, "Your OTP is:\s*(\d{6})").Groups[1].Value

$verifyBody = @{ email = $email; otp = $otp } | ConvertTo-Json
$verifyResp = Invoke-RestMethod -Uri "http://localhost:8000/api/verify-otp" -Method Post -Headers $headers -Body $verifyBody
$token = $verifyResp.access_token
$authHeaders = @{ "Content-Type" = "application/json"; "Authorization" = "Bearer $token" }

$applyResp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/apply" -Method Post -Headers $authHeaders -Body (@{ loan_type = "home_loan" } | ConvertTo-Json)
$appId = $applyResp.application_id

Write-Output "=== HOME LOAN STEPWISE START ==="
Write-Output ("application_id: " + $appId)
Write-Output ("stage: " + $applyResp.stage)

$inputs = @(
    "yes",
    "234567890123",
    "50000",
    "salaried",
    "AAAAA9999A",
    "500000",
    "10yrs",
    "33",
    "5yrs",
    "t1",
    "yes",
    "do",
    "ok",
    "do",
    "ok",
    "ok"
)

$step = 1
foreach ($msg in $inputs) {
    $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId/chat" -Method Post -Headers $authHeaders -Body (@{ message = $msg } | ConvertTo-Json)
    $last = $resp.messages[-1].content
    Write-Output ""
    Write-Output ("Step " + $step + " user: " + $msg)
    Write-Output ("Stage: " + $resp.stage + " | Status: " + $resp.status)
    if ($resp.progress) {
      Write-Output (
        "Progress: kyc=" + $resp.progress.kyc_done +
        ", credit=" + $resp.progress.credit_done +
        ", policy=" + $resp.progress.policy_done +
        ", aff=" + $resp.progress.affordability_done +
        ", risk=" + $resp.progress.risk_done +
        ", offer=" + $resp.progress.offer_done +
        ", sanction=" + $resp.progress.sanction_done
      )
    }
    Write-Output ("Assistant: " + $last)
    $step++

    if ($resp.stage -in @("await_acceptance", "completed", "rejected")) {
        break
    }
}

Write-Output "=== HOME LOAN STEPWISE END ==="