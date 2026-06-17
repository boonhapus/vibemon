# Record the SKY hatch demo with Loopi.
# Prereqs: frontend dev server at https://localhost:5173, Loopi >= 1.2.0, Playwright Chromium.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

loopi .\sky-hatch-demo.json `
  --format mp4 `
  --output .. `
  --name sky-hatch-demo `
  --speed 1.5
