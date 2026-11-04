Write-Host "--- Encendiendo AI Office Engine ---" -ForegroundColor Cyan

$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "[1/3] Iniciando Servidor de Comunicaciones (FastAPI)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit -Command `"`$env:PYTHONIOENCODING='utf-8'; .\venv\Scripts\activate; python _core_orchestrator\server.py`""

Write-Host "[2/3] Iniciando Servidor Visual (UI 2D)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit -Command `".\venv\Scripts\activate; python -m http.server 8030 --directory _ui_2d`""

Write-Host "Esperando 3 segundos para estabilizar la red..." -ForegroundColor DarkGray
Start-Sleep -Seconds 3

Write-Host "[3/3] Ejecutando Motor LangGraph..." -ForegroundColor Green
.\venv\Scripts\activate
python _core_orchestrator\graph.py
