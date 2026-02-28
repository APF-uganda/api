# PowerShell script to fix SSL issues
Write-Host "Updating SSL-related packages..." -ForegroundColor Green

# Upgrade packages
pip install --upgrade pip
pip install --upgrade requests urllib3 certifi pyOpenSSL

Write-Host "`nPackage versions:" -ForegroundColor Green
pip show requests urllib3 certifi pyOpenSSL

Write-Host "`nDone! Please restart your Django server." -ForegroundColor Green
