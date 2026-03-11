# Test Payment Status API
param(
    [string]$PaymentId = "d1eaa3df-fcca-467e-ae6e-4473a90e2c71"
)

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Testing Payment Status API" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$url = "http://localhost:8000/api/v1/payments/status/$PaymentId/"

Write-Host "Request:" -ForegroundColor Yellow
Write-Host "  URL: $url"
Write-Host "  Method: GET"
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri $url -Method Get -ContentType "application/json" -ErrorAction Stop
    
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Yellow
    $response | ConvertTo-Json -Depth 10 | Write-Host
    
    Write-Host ""
    Write-Host "Payment Status Details:" -ForegroundColor Yellow
    Write-Host "  Status: $($response.status)"
    Write-Host "  Message: $($response.message)"
    Write-Host "  Amount: $($response.amount) $($response.currency)"
    Write-Host "  Provider: $($response.provider)"
    Write-Host "  Provider Transaction ID: $($response.provider_transaction_id)"
    Write-Host "  Updated At: $($response.updated_at)"
    
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    
    if ($statusCode) {
        Write-Host "HTTP Error: $statusCode" -ForegroundColor Red
        
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host ""
            Write-Host "Error Response:" -ForegroundColor Red
            $responseBody | ConvertFrom-Json | ConvertTo-Json -Depth 10 | Write-Host
        } catch {
            Write-Host "Could not parse error response" -ForegroundColor Red
        }
    } else {
        Write-Host "ERROR: Cannot connect to server" -ForegroundColor Red
        Write-Host ""
        Write-Host "Make sure Django server is running:" -ForegroundColor Yellow
        Write-Host "  cd Backend"
        Write-Host "  python manage.py runserver"
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
