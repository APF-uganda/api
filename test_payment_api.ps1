# Test PesaPal Payment API
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Testing PesaPal Payment API" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$url = "http://localhost:8000/api/v1/payments/initiate/"

$body = @{
    phone_number = "256704138560"
    provider = "pesapal"
    amount = 50000
} | ConvertTo-Json

Write-Host "Request:" -ForegroundColor Yellow
Write-Host "  URL: $url"
Write-Host "  Body: $body"
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json" -ErrorAction Stop
    
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Yellow
    $response | ConvertTo-Json -Depth 10 | Write-Host
    
    if ($response.success) {
        Write-Host ""
        Write-Host "Payment initiated successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Payment Details:" -ForegroundColor Yellow
        Write-Host "  Payment ID: $($response.payment_id)"
        Write-Host "  Transaction Ref: $($response.transaction_reference)"
        Write-Host "  Amount: $($response.amount) $($response.currency)"
        Write-Host "  Status: $($response.status)"
        
        if ($response.redirect_url) {
            Write-Host ""
            Write-Host "Redirect URL:" -ForegroundColor Cyan
            Write-Host "  $($response.redirect_url)"
            Write-Host ""
            Write-Host "User should be redirected to this URL to complete payment" -ForegroundColor Yellow
        }
    } else {
        Write-Host ""
        Write-Host "Payment initiation failed" -ForegroundColor Red
        Write-Host "  Message: $($response.message)"
    }
    
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
