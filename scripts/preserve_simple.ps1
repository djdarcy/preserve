<#
.SYNOPSIS
    Copy a list of files to a backup root while
    ─ retaining full NTFS metadata (timestamps, ACLs, streams)
    ─ mirroring the absolute path (drive letter ⇒ first folder)
    ─ producing a hash‑verified JSON log for restore/validation.

.PARAMETER FileList
    Text file containing one absolute path per line.

.PARAMETER DestRoot
    Folder that will hold the backup (e.g. D:\Backups).

.PARAMETER HashAlgorithm
    SHA256 | SHA1 | MD5   (default = SHA256)

.PARAMETER Log
    Optional explicit path for the JSON log file.

.EXAMPLE
    .\Backup-WithRobocopy.ps1 -FileList C:\lists\files.txt `
                              -DestRoot E:\Backups `
                              -HashAlgorithm SHA256
#>

param(
    [Parameter(Mandatory)][string]$FileList,
    [Parameter(Mandatory)][string]$DestRoot,
    [ValidateSet('SHA256','SHA1','MD5')][string]$HashAlgorithm = 'SHA256',
    [string]$Log = "$(Join-Path $PSScriptRoot "backup_$((Get-Date).ToString('yyyyMMdd_HHmmss')).json")"
)

Write-Host "==> Backup started: $(Get-Date)" -ForegroundColor Cyan
if (-not (Test-Path $DestRoot)) { New-Item -ItemType Directory -Path $DestRoot -Force | Out-Null }

$report = @()

Get-Content -LiteralPath $FileList | Where-Object { $_.Trim() -ne '' } | ForEach-Object {

    $src = $_.Trim('"').Trim()

    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) {
        Write-Warning "File not found: $src"
        $report += [pscustomobject]@{ Source=$src; Status='NOT_FOUND' }
        return
    }

    # --- Build destination path -------------------------------------------------
    $drive = ($src.Substring(0,1)).ToUpper()         # 'C'
    $rel   = $src.Substring(2)                        # '\path\to\file.txt'
    $dest  = Join-Path $DestRoot ($drive + $rel)      # D:\Backups\C\path\to\file.txt
    $destDir = Split-Path $dest -Parent
    if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }

    # --- Hash source ------------------------------------------------------------
    $hashSrc = (Get-FileHash -Algorithm $HashAlgorithm -LiteralPath $src).Hash

    # --- Copy via Robocopy (preserves EVERYTHING) ------------------------------
    robocopy (Split-Path $src -Parent) $destDir ('"' + (Split-Path $src -Leaf) + '"') `
        /COPYALL /R:1 /W:1 /NFL /NDL /NP /NJH /NJS | Out-Null

    # --- Hash destination & compare --------------------------------------------
    $hashDst = (Get-FileHash -Algorithm $HashAlgorithm -LiteralPath $dest).Hash
    $status  = if ($hashSrc -eq $hashDst) { 'OK' } else { 'HASH_MISMATCH' }

    $report += [pscustomobject]@{
        Source      = $src
        Destination = $dest
        Hash        = $hashSrc
        Status      = $status
    }

    if ($status -eq 'OK') {
        Write-Host "[OK] $src ⇒ $dest"
    }
    else {
        Write-Host "[MISMATCH] $src" -ForegroundColor Red
    }
}

# --- Persist JSON log -----------------------------------------------------------
$report | ConvertTo-Json -Depth 3 | Out-File -LiteralPath $Log -Encoding UTF8
Write-Host "==> Backup finished.  Log: $Log" -ForegroundColor Cyan
