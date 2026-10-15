param([Parameter(Mandatory=$true)][string]$InputFile, [Parameter(Mandatory=$true)][string]$OutputFile)
$ErrorActionPreference = 'Stop'
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $word.Options.UpdateLinksAtOpen = $false
    $word.Options.UpdateLinksAtPrint = $false
    $word.Options.UpdateFieldsAtPrint = $false
    $confirm = $false
    $readOnly = $true
    $addRecent = $false
    $document = $word.Documents.Open([ref]$InputFile, [ref]$confirm, [ref]$readOnly, [ref]$addRecent)
    $document.ExportAsFixedFormat($OutputFile, 17)
} finally {
    $doNotSave = 0
    if ($null -ne $document) { $document.Close([ref]$doNotSave); [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) }
    if ($null -ne $word) { $word.Quit([ref]$doNotSave); [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) }
}
