$ErrorActionPreference = 'Stop'
Set-Location "c:/Users/KIIT0001/Downloads/bank-agent/backend"

try {
    $email = "e2e.test@example.com"
    $headers = @{ "Content-Type" = "application/json" }

    $otpReqBody = @{ email = $email } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://localhost:8000/api/request-otp" -Method Post -Headers $headers -Body $otpReqBody | Out-Null
    Start-Sleep -Milliseconds 700

    $otpLine = Get-Content "logs/app.log" -Tail 300 | Select-String -Pattern "Your OTP is:" | Select-Object -Last 1
    if (-not $otpLine) { throw "OTP line not found in logs" }

    $otpMatch = [regex]::Match($otpLine.Line, "Your OTP is:\s*(\d{6})")
    if (-not $otpMatch.Success) { throw "OTP parse failed" }
    $otp = $otpMatch.Groups[1].Value

    $verifyBody = @{ email = $email; otp = $otp } | ConvertTo-Json
    $verifyResp = Invoke-RestMethod -Uri "http://localhost:8000/api/verify-otp" -Method Post -Headers $headers -Body $verifyBody
    $token = $verifyResp.access_token
    if (-not $token) { throw "No token returned" }

    $authHeaders = @{ "Content-Type" = "application/json"; "Authorization" = "Bearer $token" }

    $applyBody = @{ loan_type = "personal_loan" } | ConvertTo-Json
    $applyResp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/apply" -Method Post -Headers $authHeaders -Body $applyBody
    $appId = $applyResp.application_id
    if (-not $appId) { throw "No application_id" }

    $msg1 = "My Aadhaar is 123456789012 and PAN is MIODB4596G. My monthly income is 75000. I need loan amount 300000 for 24 months. Age 30, salaried, 5 years experience, Mumbai."
    $chat1Body = @{ message = $msg1 } | ConvertTo-Json
    $chat1Resp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId/chat" -Method Post -Headers $authHeaders -Body $chat1Body

    $resp = $chat1Resp
    if ($resp.stage -eq "verify_kyc") {
        $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId/chat" -Method Post -Headers $authHeaders -Body (@{ message = "yes" } | ConvertTo-Json)
    }

    $maxSteps = 20
    $steps = 0
    while ($resp.stage -notin @("completed", "rejected", "await_acceptance") -and $steps -lt $maxSteps) {
        $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId/chat" -Method Post -Headers $authHeaders -Body (@{ message = "ok" } | ConvertTo-Json)
        $steps++
    }

    if ($resp.stage -eq "await_acceptance") {
        $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId/chat" -Method Post -Headers $authHeaders -Body (@{ message = "accept" } | ConvertTo-Json)
        $steps = 0
        while ($resp.stage -notin @("completed", "rejected") -and $steps -lt $maxSteps) {
            $resp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId/chat" -Method Post -Headers $authHeaders -Body (@{ message = "ok" } | ConvertTo-Json)
            $steps++
        }
    }

    $chat2Resp = $resp
    $loanId = $chat2Resp.loan_id
    $outPdf = $null
    if ($loanId) {
        $outPdf = "c:/Users/KIIT0001/Downloads/bank-agent/backend/sanction_letters/e2e_$loanId.pdf"
        Invoke-WebRequest -Uri "http://localhost:8000/api/loans/$loanId/sanction-letter" -Headers $authHeaders -OutFile $outPdf -UseBasicParsing | Out-Null
    }

    [ordered]@{
        otp = $otp
        application_id = $appId
        stage_after_details = $chat1Resp.stage
        stage_after_accept = $chat2Resp.stage
        status_after_accept = $chat2Resp.status
        loan_id = $loanId
        sanction_pdf = $outPdf
        final_reply = $chat2Resp.messages[-1].content
    } | ConvertTo-Json -Depth 6
}
catch {
    Write-Output "FLOW_FAILED"
    if ($_.Exception.Response -ne $null) {
        $resp = $_.Exception.Response
        Write-Output ("STATUS:" + [int]$resp.StatusCode)
        $sr = New-Object System.IO.StreamReader($resp.GetResponseStream())
        Write-Output $sr.ReadToEnd()
    }
    else {
        Write-Output $_.Exception.Message
    }
}
