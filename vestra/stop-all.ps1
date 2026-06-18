# VESTRA Shutdown — kills all uvicorn + next dev processes
Write-Host "Stopping VESTRA..." -ForegroundColor Yellow
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "node" -ErrorAction SilentlyContinue | ForEach-Object {
    try { if ((Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*next*") { $_ | Stop-Process -Force } } catch {}
}
Write-Host "VESTRA stopped." -ForegroundColor Green
