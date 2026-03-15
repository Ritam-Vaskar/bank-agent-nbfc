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

    $msg1 = "My Aadhaar is 123456789012 and PAN is ABCDE1234F. My monthly income is 75000. I need loan amount 300000 for 24 months. Age 30, salaried, 5 years experience, Mumbai."
    $chat1Body = @{ message = $msg1 } | ConvertTo-Json
    $chat1Resp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId/chat" -Method Post -Headers $authHeaders -Body $chat1Body

    $chat2Body = @{ message = "Yes, I accept the offer" } | ConvertTo-Json
    $chat2Resp = Invoke-RestMethod -Uri "http://localhost:8000/api/loans/applications/$appId/chat" -Method Post -Headers $authHeaders -Body $chat2Body
    $loanId = $chat2Resp.loan_id
    if (-not $loanId) { throw "No loan_id" }

    $outPdf = "c:/Users/KIIT0001/Downloads/bank-agent/backend/sanction_letters/e2e_$loanId.pdf"
    Invoke-WebRequest -Uri "http://localhost:8000/api/loans/$loanId/sanction-letter" -Headers $authHeaders -OutFile $outPdf -UseBasicParsing | Out-Null

    [ordered]@{
        otp = $otp
        application_id = $appId
        stage_after_details = $chat1Resp.stage
        stage_after_accept = $chat2Resp.stage
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
