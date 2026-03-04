param(
  [string]$ListenAddress = "0.0.0.0",
  [int]$ListenPort = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "[remove-portproxy] removing rule"
netsh interface portproxy delete v4tov4 listenaddress=$ListenAddress listenport=$ListenPort | Out-Null

Write-Host "[remove-portproxy] current rules:"
netsh interface portproxy show all
