#Requires -Version 5.1
param(
    [string]$ShortcutName = "Ansys Electronics Desktop 2026 R1 + Codex MCP",
    [string]$AedtExe = "G:\ANSYS206\ANSYS Inc\v261\AnsysEM\ansysedt.exe",
    [switch]$DesktopShortcut,
    [switch]$StartMenuShortcut,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LaunchScript = (Resolve-Path -LiteralPath (Join-Path $ScriptDir "launch_aedt_with_mcp_bridge.ps1")).Path
$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

if (-not $DesktopShortcut -and -not $StartMenuShortcut) {
    $DesktopShortcut = $true
    $StartMenuShortcut = $true
}

function New-AedtMcpShortcut {
    param(
        [string]$ShortcutPath
    )

    $directory = Split-Path -Parent $ShortcutPath
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    if ($DryRun) {
        Write-Host "[AEDT MCP] Would create shortcut: $ShortcutPath"
        Write-Host "[AEDT MCP] Target: $PowerShellExe"
        Write-Host "[AEDT MCP] Arguments: -NoProfile -ExecutionPolicy Bypass -File `"$LaunchScript`""
        return
    }

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $PowerShellExe
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$LaunchScript`""
    $shortcut.WorkingDirectory = $ScriptDir
    if (Test-Path -LiteralPath $AedtExe) {
        $shortcut.IconLocation = "$AedtExe,0"
    }
    $shortcut.Description = "Start Ansys Electronics Desktop and automatically load the Codex AEDT MCP bridge."
    $shortcut.Save()

    Write-Host "[AEDT MCP] Created shortcut: $ShortcutPath"
}

if (-not (Test-Path -LiteralPath $LaunchScript)) {
    throw "Launcher script was not found: $LaunchScript"
}

if ($DesktopShortcut) {
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    New-AedtMcpShortcut -ShortcutPath (Join-Path $desktopPath "$ShortcutName.lnk")
}

if ($StartMenuShortcut) {
    $startMenuPrograms = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    New-AedtMcpShortcut -ShortcutPath (Join-Path $startMenuPrograms "$ShortcutName.lnk")
}
