$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
Set-Location $PSScriptRoot
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } | Select-Object -First 1 -ExpandProperty IPAddress)
Write-Host "On this PC:  http://127.0.0.1:8000"
if ($ip) { Write-Host "On your phone (same Wi-Fi):  http://$ip`:8000" }
Write-Host "Put that phone URL into android-app/app/src/main/res/values/strings.xml as app_url"
Write-Host ""
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
