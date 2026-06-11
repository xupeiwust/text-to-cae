#Requires -Version 5.1
param(
    [string]$AedtExe = "G:\ANSYS206\ANSYS Inc\v261\AnsysEM\ansysedt.exe",
    [string]$BridgeLoader = "",
    [string]$BridgeHost = "127.0.0.1",
    [int]$BridgePort = 48252,
    [int]$WaitSeconds = 120,
    [switch]$NoLaunch,
    [switch]$SkipProbe,
    [switch]$AllowComCreate,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..")).Path

if ([string]::IsNullOrWhiteSpace($BridgeLoader)) {
    $BridgeLoader = Join-Path $RepoRoot "reload_bridge_in_aedt.py"
}

$BridgeLoader = (Resolve-Path -LiteralPath $BridgeLoader).Path
$ProjectPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

function Write-Step {
    param([string]$Message)
    Write-Host "[AEDT MCP] $Message"
}

function Get-AedtDesktop {
    param([switch]$AllowCreate)

    $progIds = @(
        "Ansoft.ElectronicsDesktop.2026.1",
        "Ansoft.ElectronicsDesktop"
    )

    foreach ($progId in $progIds) {
        try {
            $app = [System.Runtime.InteropServices.Marshal]::GetActiveObject($progId)
            if ($null -ne $app) {
                $desktop = $app.GetAppDesktop()
                if ($null -ne $desktop) {
                    $version = $desktop.GetVersion()
                    return [pscustomobject]@{
                        Desktop = $desktop
                        Version = $version
                        ProgId = $progId
                        Source = "running"
                    }
                }
            }
        }
        catch {
            # AEDT has not registered this ProgID in the Running Object Table yet.
        }

        if (-not $AllowCreate) {
            continue
        }

        try {
            $type = [type]::GetTypeFromProgID($progId)
            if ($null -eq $type) {
                continue
            }

            $app = [Activator]::CreateInstance($type)
            if ($null -eq $app) {
                continue
            }

            $desktop = $app.GetAppDesktop()
            if ($null -eq $desktop) {
                continue
            }

            $version = $desktop.GetVersion()
            return [pscustomobject]@{
                Desktop = $desktop
                Version = $version
                ProgId = $progId
                Source = "created"
            }
        }
        catch {
            continue
        }
    }

    return $null
}

function Wait-AedtDesktop {
    param(
        [int]$TimeoutSeconds,
        [switch]$AllowCreate
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $desktopInfo = Get-AedtDesktop -AllowCreate:$AllowCreate
        if ($null -ne $desktopInfo) {
            return $desktopInfo
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for AEDT COM desktop after $TimeoutSeconds seconds."
}

function Invoke-BridgeProbe {
    if (-not (Test-Path -LiteralPath $ProjectPython)) {
        Write-Warning "Project Python was not found at $ProjectPython; bridge probe skipped."
        return
    }

$probeCode = @"
import json
from aedt_socket_protocol import request

result = request('$BridgeHost', $BridgePort, 'ping', timeout=10.0)
print(json.dumps(result, ensure_ascii=False, indent=2))
"@

    Push-Location $RepoRoot
    try {
        & $ProjectPython -c $probeCode
        if ($LASTEXITCODE -ne 0) {
            throw "Bridge probe failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

if ($DryRun) {
    Write-Step "AEDT executable: $AedtExe"
    Write-Step "Bridge loader: $BridgeLoader"
    Write-Step "Bridge endpoint: $BridgeHost`:$BridgePort"
    Write-Step "Project root: $RepoRoot"
    Write-Step "Project Python: $ProjectPython"
    Write-Step "Allow COM CreateInstance fallback: $([bool]$AllowComCreate)"
    exit 0
}

if (-not (Test-Path -LiteralPath $AedtExe)) {
    throw "AEDT executable was not found: $AedtExe"
}

$allowCreateForThisRun = [bool]$AllowComCreate

if (-not $NoLaunch) {
    $running = Get-Process -Name "ansysedt" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $running) {
        Write-Step "No AEDT process was found; starting AEDT through COM CreateInstance."
        $allowCreateForThisRun = $true
    }
    else {
        Write-Step "AEDT is already running; reusing the existing session without COM CreateInstance."
    }
}
else {
    Write-Step "NoLaunch was set; waiting for an existing AEDT session."
}

$desktopInfo = Wait-AedtDesktop -TimeoutSeconds $WaitSeconds -AllowCreate:$allowCreateForThisRun
Write-Step "Connected to AEDT $($desktopInfo.Version) through $($desktopInfo.ProgId) [$($desktopInfo.Source)]."

Write-Step "Loading bridge script into AEDT: $BridgeLoader"
try {
    $desktopInfo.Desktop.RunScript($BridgeLoader) | Out-Null
}
catch {
    throw "AEDT RunScript failed for $BridgeLoader. Original error: $($_.Exception.Message)"
}

if (-not $SkipProbe) {
    Write-Step "Verifying raw TCP bridge on $BridgeHost`:$BridgePort."
    Invoke-BridgeProbe
}

Write-Step "AEDT MCP bridge is ready."
