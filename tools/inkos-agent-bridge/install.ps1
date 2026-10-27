# Install the agent bridge on Windows (Claude Code / Codex CLI / Grok CLI on your PC).
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Project C:\novels\my-novel [-InstallInkos 1.8.0] [-Force]
# No API keys are read or written.
param([string]$Project = "", [string]$InstallInkos = "", [switch]$Force)
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python 3 is required (python.org installer, tick 'Add to PATH')."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js is required." }
$nodeMajor = [int]((node -p "process.versions.node.split('.')[0]").Trim())
if ($nodeMajor -lt 22) { throw "Node $(node --version) is too old: InkOS needs Node 22+ (2.0 source: 22.16+)." }
if ($InstallInkos -and -not (Get-Command inkos -ErrorAction SilentlyContinue)) {
  npm install -g "@actalk/inkos@$InstallInkos"
}
if (-not (Get-Command inkos -ErrorAction SilentlyContinue)) {
  Write-Host "note: 'inkos' not on PATH; set INKOS_BIN to the inkos command or a 2.0 build's packages\cli\dist\index.js"
}

# Put the package folder on the user PATH so 'inkos-agent' (inkos-agent.cmd) works in new shells.
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ";") -notcontains $Here) {
  [Environment]::SetEnvironmentVariable("Path", "$userPath;$Here", "User")
  Write-Host "added $Here to your user PATH (open a new terminal)"
}

if ($Project) {
  New-Item -ItemType Directory -Force -Path (Join-Path $Project ".claude\agents") | Out-Null
  foreach ($f in @("AGENTS.md", "CLAUDE.md", "GROK.md", ".claude\agents\inkos-writer.md", ".claude\agents\inkos-reviewer.md")) {
    $src = Join-Path $Here $f; $dest = Join-Path $Project $f
    if ((Test-Path $dest) -and -not $Force -and ((Get-FileHash $src).Hash -ne (Get-FileHash $dest).Hash)) {
      Copy-Item $src "$dest.inkos-agent"
      Write-Host "kept your $f; new version written to $f.inkos-agent (merge it by hand)"
    } else { Copy-Item $src $dest -Force }
  }
  $ignore = Join-Path $Project ".gitignore"
  if (-not (Test-Path $ignore)) { New-Item $ignore | Out-Null }
  foreach ($line in @("runtime/", "inkos.pre-agent.json")) {
    if (-not (Select-String -Path $ignore -SimpleMatch -Pattern $line -Quiet)) { Add-Content $ignore $line }
  }
  [Environment]::SetEnvironmentVariable("INKOS_AGENT_PROJECT", $Project, "User")
  Write-Host "project ready: $Project"
}
Write-Host "Next (new terminal): inkos-agent doctor; inkos-agent start"
