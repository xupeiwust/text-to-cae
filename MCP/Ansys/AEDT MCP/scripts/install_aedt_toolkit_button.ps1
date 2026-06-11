#Requires -Version 5.1
param(
    [string]$AedtRoot = "G:\ANSYS206\ANSYS Inc\v261\AnsysEM",
    [string[]]$Toolkits = @("HFSS", "Project"),
    [string]$StartButtonLabel = "Start AEDT MCP Bridge",
    [string]$StopButtonLabel = "Stop AEDT MCP Bridge",
    [string]$PanelLabel = "Codex MCP",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..")).Path
$BridgeLoader = (Resolve-Path -LiteralPath (Join-Path $RepoRoot "reload_bridge_in_aedt.py")).Path
$BridgeStopper = (Resolve-Path -LiteralPath (Join-Path $RepoRoot "stop_bridge_in_aedt.py")).Path
$ObsoleteControlToolkitScriptName = "AEDT MCP.py"
$StartToolkitScriptName = "Start AEDT MCP Bridge.py"
$StopToolkitScriptName = "Stop AEDT MCP Bridge.py"

function Write-Step {
    param([string]$Message)
    Write-Host "[AEDT MCP] $Message"
}

function New-ToolkitScriptText {
    param(
        [string]$EntryPointPath,
        [string]$DocString
    )

    return @"
# -*- coding: utf-8 -*-
"""$DocString"""

from __future__ import print_function


ENTRY_POINT_PATH = r"$EntryPointPath"


with open(ENTRY_POINT_PATH, "r") as handle:
    code = handle.read()

exec(compile(code, ENTRY_POINT_PATH, "exec"), globals(), globals())
"@
}

function Remove-XmlNodes {
    param(
        [xml]$Xml,
        [string]$XPath
    )

    $nodes = @($Xml.SelectNodes($XPath))
    foreach ($node in $nodes) {
        if ($null -ne $node.ParentNode) {
            [void]$node.ParentNode.RemoveChild($node)
        }
    }
}

function New-CommandButton {
    param(
        [xml]$Xml,
        [string]$Label,
        [string]$ScriptName,
        [string]$Tooltip
    )

    $button = $Xml.CreateElement("button")
    $button.SetAttribute("label", $Label)
    $button.SetAttribute("script", [System.IO.Path]::GetFileNameWithoutExtension($ScriptName))
    $button.SetAttribute("tooltip", $Tooltip)
    return $button
}

function Set-ToolkitButtons {
    param(
        [xml]$Xml,
        [System.Xml.XmlElement]$Panel,
        [string]$ToolkitName
    )

    Remove-XmlNodes -Xml $Xml -XPath "//gallery[button[@label='AEDT MCP']]"
    Remove-XmlNodes -Xml $Xml -XPath "//button[@label='AEDT MCP']"
    Remove-XmlNodes -Xml $Xml -XPath "//button[@label='$StartButtonLabel']"
    Remove-XmlNodes -Xml $Xml -XPath "//button[@label='$StopButtonLabel']"

    $buttonImage = "images/pyansys_beta.png"
    if ($ToolkitName -eq "HFSS") {
        $buttonImage = "Toolkit_Images\mimo2_large.png"
    }

    $startButton = New-CommandButton `
        -Xml $Xml `
        -Label $StartButtonLabel `
        -ScriptName $StartToolkitScriptName `
        -Tooltip "Start or reload the Codex AEDT MCP raw TCP bridge on 127.0.0.1:48252."
    $startButton.SetAttribute("isLarge", "1")
    $startButton.SetAttribute("image", $buttonImage)

    $stopButton = New-CommandButton `
        -Xml $Xml `
        -Label $StopButtonLabel `
        -ScriptName $StopToolkitScriptName `
        -Tooltip "Stop the Codex AEDT MCP raw TCP bridge so AEDT can close cleanly."
    $stopButton.SetAttribute("isLarge", "1")
    $stopButton.SetAttribute("image", $buttonImage)

    [void]$Panel.AppendChild($startButton)
    [void]$Panel.AppendChild($stopButton)
}

function Install-ToolkitButton {
    param([string]$ToolkitName)

    $toolkitDir = Join-Path (Join-Path $AedtRoot "syslib\Toolkits") $ToolkitName
    $tabConfigPath = Join-Path $toolkitDir "TabConfig.xml"
    $obsoleteControlToolkitScriptPath = Join-Path $toolkitDir $ObsoleteControlToolkitScriptName
    $startToolkitScriptPath = Join-Path $toolkitDir $StartToolkitScriptName
    $stopToolkitScriptPath = Join-Path $toolkitDir $StopToolkitScriptName

    if (-not (Test-Path -LiteralPath $tabConfigPath)) {
        throw "TabConfig.xml was not found for toolkit '$ToolkitName': $tabConfigPath"
    }

    Write-Step "Target toolkit: $ToolkitName"
    Write-Step "TabConfig: $tabConfigPath"
    Write-Step "Start script: $startToolkitScriptPath"
    Write-Step "Stop script: $stopToolkitScriptPath"

    if ($DryRun) {
        Write-Step "DryRun: would back up and update $tabConfigPath"
        Write-Step "DryRun: would remove obsolete $obsoleteControlToolkitScriptPath if present"
        Write-Step "DryRun: would write $startToolkitScriptPath"
        Write-Step "DryRun: would write $stopToolkitScriptPath"
        return
    }

    $backupPath = "$tabConfigPath.bak_aedt_mcp"
    if (-not (Test-Path -LiteralPath $backupPath)) {
        Copy-Item -LiteralPath $tabConfigPath -Destination $backupPath -Force
        Write-Step "Backup created: $backupPath"
    }

    $startScriptText = New-ToolkitScriptText `
        -EntryPointPath $BridgeLoader `
        -DocString "Start or reload the Codex AEDT MCP bridge from an AEDT Toolkit button."
    $stopScriptText = New-ToolkitScriptText `
        -EntryPointPath $BridgeStopper `
        -DocString "Stop the Codex AEDT MCP bridge from an AEDT Toolkit button."
    Set-Content -LiteralPath $startToolkitScriptPath -Value $startScriptText -Encoding UTF8
    Set-Content -LiteralPath $stopToolkitScriptPath -Value $stopScriptText -Encoding UTF8
    if (Test-Path -LiteralPath $obsoleteControlToolkitScriptPath) {
        Remove-Item -LiteralPath $obsoleteControlToolkitScriptPath -Force
        Write-Step "Removed obsolete control script: $obsoleteControlToolkitScriptPath"
    }

    [xml]$xml = Get-Content -LiteralPath $tabConfigPath -Encoding UTF8
    if ($null -eq $xml.TabConfig) {
        throw "Unexpected TabConfig structure in $tabConfigPath"
    }

    $panel = $xml.SelectSingleNode("//panel[@label='$PanelLabel']")
    if ($null -eq $panel) {
        $panel = $xml.CreateElement("panel")
        $panel.SetAttribute("label", $PanelLabel)
        [void]$xml.TabConfig.AppendChild($panel)
    }

    Set-ToolkitButtons -Xml $xml -Panel $panel -ToolkitName $ToolkitName

    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Indent = $true
    $settings.Encoding = New-Object System.Text.UTF8Encoding($false)
    $writer = [System.Xml.XmlWriter]::Create($tabConfigPath, $settings)
    try {
        $xml.Save($writer)
    }
    finally {
        $writer.Close()
    }

    Write-Step "Installed stable buttons '$StartButtonLabel' and '$StopButtonLabel' into $ToolkitName."
}

if (-not (Test-Path -LiteralPath $AedtRoot)) {
    throw "AEDT root was not found: $AedtRoot"
}

foreach ($toolkit in $Toolkits) {
    Install-ToolkitButton -ToolkitName $toolkit
}

Write-Step "Done. If AEDT is already open, run oDesktop.RefreshToolkitUI() or restart AEDT to refresh the Automation ribbon."
