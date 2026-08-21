. .\test_runner.ps1

Write-Host "Running A..."
$A_res = Log-And-Run "az account show" {
    az account show --query "{id:id,name:name,tenantId:tenantId,user:user.name}" -o json 2>&1
}
Write-Host "A Result: $A_res"

Write-Host "Running B..."
# For az bicep build, we report only exit code and diagnostics, not ARM JSON.
# We will capture stdout and stderr, check exit code, and then filter.
$B_exitCode = 0
$B_diag = ""
$B_res = Log-And-Run "az bicep build" {
    # Run bicep build and capture stderr, redirecting stdout to a variable or out-null if we don't want stdout
    $diag_temp = [System.Collections.Generic.List[string]]::new()
    $proc = Start-Process -FilePath "az" -ArgumentList "bicep build --file infra/main.bicep --stdout" -NoNewWindow -RedirectStandardError "b_std_err.log" -RedirectStandardOutput "b_std_out.log" -PassThru
    $proc.WaitForExit()
    $B_exitCode = $proc.ExitCode
    $global:B_exitCode_global = $B_exitCode
    $global:B_diag_global = Get-Content "b_std_err.log" -Raw
    Remove-Item "b_std_out.log" -ErrorAction SilentlyContinue
    Remove-Item "b_std_err.log" -ErrorAction SilentlyContinue
    $LASTEXITCODE = $B_exitCode
}
Write-Host "B Exit Code: $B_exitCode_global"
Write-Host "B Diag: $B_diag_global"

Write-Host "Running C..."
$C_res = Log-And-Run "az acr check-name" {
    az acr check-name --name crbankalfadev39c7 --subscription ac021984-29ca-42e6-9c21-36e599814543 -o json 2>&1
}
Write-Host "C Result: $C_res"

Write-Host "Running D..."
$D_res = Log-And-Run "az keyvault show" {
    az keyvault show --name kv-bank-alfa-dev-39c7 --subscription ac021984-29ca-42e6-9c21-36e599814543 -o json 2>&1
}
Write-Host "D Result: $D_res"

Write-Host "Running E..."
$E_res = Log-And-Run "az ad signed-in-user show" {
    az ad signed-in-user show --query id -o tsv 2>&1
}
Write-Host "E Result: $E_res"

$F_res = $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Running F..."
    # clean userId in case of any trailing spaces/newlines
    $userId = ($E_res -join "").Trim()
    $F_res = Log-And-Run "az role assignment list" {
        az role assignment list --assignee $userId --scope /subscriptions/ac021984-29ca-42e6-9c21-36e599814543 --include-inherited --query "[].roleDefinitionName" -o tsv 2>&1
    }
    Write-Host "F Result: $F_res"
} else {
    Write-Host "E failed, skipping F."
}

Write-Host "Running G..."
$G_res = Log-And-Run "az group show" {
    az group show --name rg-voice-mortgage-app --subscription ac021984-29ca-42e6-9c21-36e599814543 --query "{name:name,location:location,id:id}" -o json 2>&1
}
Write-Host "G Result: $G_res"

Write-Host "Running H..."
$tempFile = [System.IO.Path]::GetTempFileName()
$H_res = Log-And-Run "az deployment sub what-if" {
    az deployment sub what-if --name app-onboard-deploy-39c70e04 --location swedencentral --template-file infra/main.bicep --parameters '@infra/main.parameters.json' --subscription ac021984-29ca-42e6-9c21-36e599814543 --what-if-result-format FullResourcePayloads -o json > $tempFile 2>&1
}
$temp_content = Get-Content $tempFile -Raw
Remove-Item $tempFile -ErrorAction SilentlyContinue
$global:H_full_out = $temp_content
Write-Host "H executed. Saved output length: $($temp_content.Length)"

# Save all results to a shared global variable/state for reporting
$global:A_res_out = $A_res
$global:C_res_out = $C_res
$global:D_res_out = $D_res
$global:E_res_out = $E_res
$global:F_res_out = $F_res
$global:G_res_out = $G_res

