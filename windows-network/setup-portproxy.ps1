param(
  [string]$ListenAddress = "0.0.0.0",
  [int]$ListenPort = 8000,
  [Parameter(Mandatory = $true)][string]$ConnectAddress,
  [int]$ConnectPort = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "[setup-portproxy] remove existing rule if exists"
netsh interface portproxy delete v4tov4 listenaddress=$ListenAddress listenport=$ListenPort | Out-Null

Write-Host "[setup-portproxy] add rule"
netsh interface portproxy add v4tov4 `
  listenaddress=$ListenAddress `
  listenport=$ListenPort `
  connectaddress=$ConnectAddress `
  connectport=$ConnectPort `
  protocol=tcp | Out-Null

Write-Host "[setup-portproxy] current rules:"
netsh interface portproxy show all
