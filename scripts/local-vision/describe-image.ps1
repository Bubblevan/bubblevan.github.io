param(
  [Parameter(Mandatory = $true)]
  [string]$ImagePath,

  [string]$Prompt = "You are Bubblevan's local vision OCR helper. Do not output reasoning. Output in Simplified Chinese, but use these exact ASCII section headings: ### OCR, ### Image Understanding, ### Summary. Task: extract all visible text faithfully, preserve structure such as titles, bullets, tables, captions, code, and error messages, then describe the non-text visual context, then summarize the key information. Mark uncertain text with [uncertain].",

  [string]$ModelPath = "D:\MyLab\Hugo\MiniCPM-V-4_5\ggml-model-Q8_0.gguf",

  [string]$MmprojPath = "D:\MyLab\Hugo\MiniCPM-V-4_5\mmproj-model-f16.gguf",

  [string]$LlamaCli = "C:\Users\bubblevan\AppData\Local\Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-cli.exe",

  [int]$Context = 4096,

  [int]$GpuLayers = 99,

  [int]$MaxTokens = 10240,

  [switch]$Raw
)

$ErrorActionPreference = "Stop"

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
if ($env:OS -eq "Windows_NT") {
  & chcp.com 65001 | Out-Null
}

function Resolve-ExistingPath {
  param(
    [Parameter(Mandatory = $true)]
    [string]$PathValue,

    [Parameter(Mandatory = $true)]
    [string]$Label
  )

  $resolved = Resolve-Path -LiteralPath $PathValue -ErrorAction SilentlyContinue
  if (-not $resolved) {
    throw "$Label not found: $PathValue"
  }
  return $resolved.Path
}

function Remove-ThinkingBlocks {
  param([string]$Text)

  $clean = $Text -replace '(?s)\[Start thinking\].*?\[End thinking\]', ''
  $clean = $clean -replace '(?s)\[Start thinking\].*?(?=(### OCR|### Image Understanding|### Summary|OCR|$))', ''
  $clean = $clean -replace '(?m)^\s*\[ Prompt:.*$', ''
  $clean = $clean -replace '(?m)^Loaded media from .*$',''
  $clean = $clean -replace '(?m)^Loading model.*$',''
  $clean = $clean -replace '(?m)^build\s+:.*$',''
  $clean = $clean -replace '(?m)^model\s+:.*$',''
  $clean = $clean -replace '(?m)^ftype\s+:.*$',''
  $clean = $clean -replace '(?m)^modalities\s+:.*$',''
  $clean = $clean -replace '(?m)^available commands:.*$',''
  $clean = $clean -replace '(?m)^\s*/exit or Ctrl\+C.*$',''
  $clean = $clean -replace '(?m)^\s*/regen.*$',''
  $clean = $clean -replace '(?m)^\s*/clear.*$',''
  $clean = $clean -replace '(?m)^\s*/read <file>.*$',''
  $clean = $clean -replace '(?m)^\s*/glob <pattern>.*$',''
  $clean = $clean -replace '(?m)^\s*/image <file>.*$',''
  $clean = $clean -replace '(?m)^\s*/video <file>.*$',''
  $clean = $clean -replace '(?m)^>\s*.*$',''
  $clean = $clean -replace '(?m)^Exiting\.\.\.\s*$',''

  $ocrIndex = $clean.IndexOf("### OCR", [System.StringComparison]::OrdinalIgnoreCase)
  if ($ocrIndex -ge 0) {
    $clean = $clean.Substring($ocrIndex)
  }

  return $clean.Trim()
}

$image = Resolve-ExistingPath -PathValue $ImagePath -Label "Image"
$model = Resolve-ExistingPath -PathValue $ModelPath -Label "Model"
$mmproj = Resolve-ExistingPath -PathValue $MmprojPath -Label "MMProj"

$cmd = Get-Command $LlamaCli -ErrorAction SilentlyContinue
if (-not $cmd) {
  throw "Cannot find llama-cli command: $LlamaCli. Pass -LlamaCli with the full executable path."
}

$arguments = @(
  "-m", $model,
  "--mmproj", $mmproj,
  "--image", $image,
  "-p", $Prompt,
  "-c", "$Context",
  "-ngl", "$GpuLayers",
  "-n", "$MaxTokens",
  "--single-turn",
  "--no-display-prompt"
)

$output = & $cmd.Source @arguments 2>&1
$text = ($output | Out-String)

if ($Raw) {
  $text.Trim()
} else {
  Remove-ThinkingBlocks -Text $text
}
