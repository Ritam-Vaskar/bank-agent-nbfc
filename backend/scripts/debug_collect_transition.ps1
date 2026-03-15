$ErrorActionPreference = 'Stop'
Set-Location "c:/Users/KIIT0001/Downloads/bank-agent/backend"

$email = "debug.collect@example.com"
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

$applyResp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/apply" -Method Post -Headers $authHeaders -Body (@{ loan_type = "personal_loan" } | ConvertTo-Json)
$appId = $applyResp.application_id

$required = @('aadhaar','pan','monthly_income','requested_amount','tenure_months','age','employment_type','employment_years','city_tier')
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
    Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId/chat" -Method Post -Headers $authHeaders -Body (@{ message = $msg } | ConvertTo-Json) | Out-Null
    $app = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId" -Method Get -Headers $authHeaders
    $appData = $app.application_data
    $keys = @($appData.PSObject.Properties.Name)
    $missing = @()
    foreach ($f in $required) {
        if (-not $keys.Contains($f) -or $null -eq $appData.$f -or $appData.$f -eq "") {
            $missing += $f
        }
    }

    Write-Output ""
    Write-Output ("Step " + $step + " msg: " + $msg)
    Write-Output ("stage=" + $app.workflow_stage + " status=" + $app.status)
    Write-Output ("keys=" + ($keys -join ','))
    Write-Output ("missing=" + ($missing -join ','))

    $step++
}
