param(
  [ValidateSet("win-x64","win-x86","win-arm64")]
  [string]$Runtime = "win-x64",
  [ValidateSet("Debug","Release")]
  [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$proj = Join-Path $PSScriptRoot "IronHub.AccessAgent.csproj"

dotnet build $proj -c $Configuration
dotnet publish $proj -c $Configuration -r $Runtime -p:PublishSingleFile=true -p:SelfContained=false

$out = Join-Path $PSScriptRoot ("bin/{0}/net8.0-windows/{1}/publish" -f $Configuration, $Runtime)
Write-Host ("OK: " + $out)

