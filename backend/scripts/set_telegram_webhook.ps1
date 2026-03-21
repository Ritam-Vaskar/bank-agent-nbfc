param(
    [string]$WebhookBaseUrl = "",
    [switch]$DropPendingUpdates = $false
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Resolve-Path (Join-Path $scriptDir "..")
$envPath = Join-Path $backendDir ".env"

if (!(Test-Path $envPath)) {
    throw "backend/.env not found at $envPath"
}

$envMap = @{}
Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $parts = $_ -split '=', 2
    if ($parts.Count -eq 2) {
        $envMap[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$botToken = $envMap["TELEGRAM_BOT_TOKEN"]
$secretToken = $envMap["TELEGRAM_WEBHOOK_SECRET"]
$defaultBaseUrl = $envMap["BACKEND_URL"]

if ([string]::IsNullOrWhiteSpace($WebhookBaseUrl)) {
    $WebhookBaseUrl = $defaultBaseUrl
}

if ([string]::IsNullOrWhiteSpace($botToken)) {
    throw "TELEGRAM_BOT_TOKEN is missing in backend/.env"
}

if ([string]::IsNullOrWhiteSpace($secretToken)) {
    throw "TELEGRAM_WEBHOOK_SECRET is missing in backend/.env"
}

if ([string]::IsNullOrWhiteSpace($WebhookBaseUrl)) {
    throw "Webhook base URL is required. Pass -WebhookBaseUrl https://your-domain"
}

if ($WebhookBaseUrl -notmatch '^https://') {
    throw "Webhook URL must be HTTPS and publicly reachable by Telegram. Current: $WebhookBaseUrl"
}

$webhookUrl = "$($WebhookBaseUrl.TrimEnd('/'))/api/telegram/webhook"
$telegramApi = "https://api.telegram.org/bot$botToken"

Write-Host "Setting Telegram webhook to: $webhookUrl" -ForegroundColor Cyan

$setBody = @{
    url = $webhookUrl
    secret_token = $secretToken
    allowed_updates = @("message", "edited_message")
    drop_pending_updates = [bool]$DropPendingUpdates
} | ConvertTo-Json -Depth 4

$setResponse = Invoke-RestMethod -Uri "$telegramApi/setWebhook" -Method Post -ContentType "application/json" -Body $setBody
$infoResponse = Invoke-RestMethod -Uri "$telegramApi/getWebhookInfo" -Method Get

Write-Host "setWebhook response:" -ForegroundColor Green
$setResponse | ConvertTo-Json -Depth 6
Write-Host "getWebhookInfo response:" -ForegroundColor Green
$infoResponse | ConvertTo-Json -Depth 8
