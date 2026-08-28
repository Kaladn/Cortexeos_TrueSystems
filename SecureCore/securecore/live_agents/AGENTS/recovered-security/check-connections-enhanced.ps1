param(
    [string]$OutDir = "$env:USERPROFILE\Desktop\Security",
    [switch]$BlockMeta,
    [switch]$BlockEgyptIP
)

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$CaseDir = Join-Path $OutDir "case_$Stamp"
New-Item -ItemType Directory -Path $CaseDir -Force | Out-Null

Write-Host "Security check started: $Stamp"
Write-Host "Output: $CaseDir"

# Network
Get-NetTCPConnection |
    Export-Csv "$CaseDir\tcp_connections.csv" -NoTypeInformation

Get-NetUDPEndpoint |
    Export-Csv "$CaseDir\udp_endpoints.csv" -NoTypeInformation

# Processes
Get-Process |
    Select-Object Name,Id,Path,StartTime,Company,Description |
    Export-Csv "$CaseDir\processes.csv" -NoTypeInformation

# Services
Get-CimInstance Win32_Service |
    Select-Object Name,DisplayName,State,StartMode,PathName,ProcessId |
    Export-Csv "$CaseDir\services.csv" -NoTypeInformation

# Scheduled tasks
Get-ScheduledTask |
    Select-Object TaskName,TaskPath,State |
    Export-Csv "$CaseDir\scheduled_tasks.csv" -NoTypeInformation

# DNS cache
Get-DnsClientCache |
    Export-Csv "$CaseDir\dns_cache.csv" -NoTypeInformation

# Startup folders
$StartupPaths = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"
)

$StartupReport = foreach ($path in $StartupPaths) {
    if (Test-Path $path) {
        Get-ChildItem $path -Force | Select-Object FullName,Length,LastWriteTime
    }
}
$StartupReport | Export-Csv "$CaseDir\startup_items.csv" -NoTypeInformation

# Registry persistence
$RunKeys = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce"
)

$RegReport = foreach ($key in $RunKeys) {
    if (Test-Path $key) {
        Get-ItemProperty $key | Select-Object *
    }
}
$RegReport | Out-File "$CaseDir\registry_run_keys.txt"

# Optional blocks
if ($BlockEgyptIP) {
    netsh advfirewall firewall add rule name="BLOCK: Tedata Egypt 57.144.174.141 ALL TCP" dir=out action=block remoteip=57.144.174.141 protocol=tcp
    netsh advfirewall firewall add rule name="BLOCK: Tedata Egypt 57.144.174.141 ALL UDP" dir=out action=block remoteip=57.144.174.141 protocol=udp
}

if ($BlockMeta) {
    netsh advfirewall firewall add rule name="BLOCK: Facebook Meta IPv4" dir=out action=block remoteip="31.13.64.0/18,66.220.144.0/20,69.171.224.0/19,103.4.96.0/22,129.134.0.0/16,157.240.0.0/16,173.252.64.0/18,179.60.192.0/22,185.60.216.0/22,204.15.20.0/22" protocol=any
    netsh advfirewall firewall add rule name="BLOCK: Facebook Meta IPv6" dir=out action=block remoteip="2a03:2880::/32,2a03:2887::/32" protocol=any
}

# Firewall rule snapshot
Get-NetFirewallRule |
    Where-Object {
        $_.DisplayName -like "*Tedata*" -or
        $_.DisplayName -like "*Egypt*" -or
        $_.DisplayName -like "*Facebook*" -or
        $_.DisplayName -like "*Meta*"
    } |
    Select-Object DisplayName,Direction,Action,Enabled |
    Export-Csv "$CaseDir\firewall_security_rules.csv" -NoTypeInformation

Write-Host "Security check complete."
Write-Host "Files saved to: $CaseDir"
