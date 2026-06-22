# Start the PolyLife core (Windows).  Run from anywhere:  scripts\start-core.ps1
# Builds the frontend + backend in Docker and serves on http://localhost:8000
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    docker compose up --build
} finally {
    Pop-Location
}
