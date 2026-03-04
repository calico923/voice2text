param(
  [string]$RuleName = "voice2text-realtime-8000",
  [int]$Port = 8000,
  [Parameter(Mandatory = $true)][string]$MacIp
)

$ErrorActionPreference = "Stop"

Write-Host "[setup-firewall-rule] reset existing rule"
Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule

Write-Host "[setup-firewall-rule] add inbound allow rule (TCP/$Port, RemoteAddress=$MacIp)"
New-NetFirewallRule `
  -DisplayName $RuleName `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort $Port `
  -RemoteAddress $MacIp | Out-Null

Write-Host "[setup-firewall-rule] effective rule:"
Get-NetFirewallRule -DisplayName $RuleName | Get-NetFirewallAddressFilter | Format-List
