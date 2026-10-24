# Doctor PC only. Preview is default; -Apply requires administrator review.
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)][ipaddress]$DoctorAddress,
    [Parameter(Mandatory)][ipaddress]$ReceptionAddress,
    [ValidateRange(1024,65535)][int]$HttpsPort = 8443,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
if ($HttpsPort -eq 5432) { throw 'HTTPS cannot use the database port' }
if ($DoctorAddress.Equals($ReceptionAddress)) { throw 'Reservations must differ' }
foreach ($address in @($DoctorAddress, $ReceptionAddress)) {
    if ($address.IPAddressToString -notmatch '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)') {
        throw 'Use explicit reserved RFC1918 IPv4 addresses'
    }
}
$preview = -not $Apply
if ($PSCmdlet.ShouldProcess('Doctor PC', 'Create scoped clinic firewall rules')) {
    New-NetFirewallRule -Name 'Clinic-HTTPS' -DisplayName 'Clinic HTTPS from receptionist' `
        -Direction Inbound -Action Allow -Protocol TCP -LocalPort $HttpsPort `
        -LocalAddress $DoctorAddress.IPAddressToString `
        -RemoteAddress $ReceptionAddress.IPAddressToString -Profile Private -WhatIf:$preview
    New-NetFirewallRule -Name 'Clinic-Block-DB-LAN' -DisplayName 'Block inbound clinic database' `
        -Direction Inbound -Action Block -Protocol TCP -LocalPort 5432 -Profile Any -WhatIf:$preview
}
# Does not delete existing rules or change default firewall policies.
# Audit existing broad allow rules and enabled Private-profile default inbound block.
