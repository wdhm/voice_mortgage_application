function Log-And-Run($label, $cmdBlock) {
    $isoTimeStart = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss%Z")
    Add-Content -Path ".copilot-azure/sessions/39c70e04-2401-4383-afef-e5e8b89e37bc/deploy-audit.log" -Value "$isoTimeStart | $label | started"
    $result = $null
    $success = $false
    $exitCode = 0
    try {
        $result = & $cmdBlock
        $exitCode = $LASTEXITCODE
        if ($LASTEXITCODE -eq 0) {
            $success = $true
        }
    } catch {
        $exitCode = 1
        $success = $false
    } finally {
        $isoTimeEnd = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss%Z")
        if ($success) {
            Add-Content -Path ".copilot-azure/sessions/39c70e04-2401-4383-afef-e5e8b89e37bc/deploy-audit.log" -Value "$isoTimeEnd | $label | succeeded"
        } else {
            Add-Content -Path ".copilot-azure/sessions/39c70e04-2401-4383-afef-e5e8b89e37bc/deploy-audit.log" -Value "$isoTimeEnd | $label | failed (exit $exitCode)"
        }
    }
    return $result
}
