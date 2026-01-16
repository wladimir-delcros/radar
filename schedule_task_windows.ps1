# Script PowerShell pour creer une tache planifiee Windows
# Execute le script Python quotidiennement a 9h00
# Encodage: UTF-8 sans BOM pour compatibilite

# Verifier les droits administrateur
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERREUR: Ce script necessite les droits administrateur!" -ForegroundColor Red
    Write-Host "Veuillez executer PowerShell en tant qu'administrateur" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Pour executer en tant qu'administrateur:" -ForegroundColor Cyan
    Write-Host "  1. Clic droit sur PowerShell" -ForegroundColor White
    Write-Host "  2. Selectionner 'Executer en tant qu'administrateur'" -ForegroundColor White
    Write-Host "  3. Naviguer vers le dossier: $PSScriptRoot" -ForegroundColor White
    Write-Host "  4. Executer: .\schedule_task_windows.ps1" -ForegroundColor White
    exit 1
}

$scriptPath = Join-Path $PSScriptRoot "linkedin_scraper_company.py"

# Verifier que le script Python existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "ERREUR: Script Python introuvable: $scriptPath" -ForegroundColor Red
    exit 1
}

# Trouver Python
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $pythonExe) {
    $pythonExe = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}

if (-not $pythonExe) {
    Write-Host "ERREUR: Python n'est pas trouve dans le PATH" -ForegroundColor Red
    Write-Host "Veuillez installer Python ou l'ajouter au PATH" -ForegroundColor Yellow
    exit 1
}

Write-Host "Python trouve: $pythonExe" -ForegroundColor Green

$taskName = "LinkedInScraper_Companies"
$description = "Recupere quotidiennement le dernier post LinkedIn des entreprises listees dans companies_to_follow.csv"

# Supprimer la tache existante si elle existe
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Suppression de la tache existante..." -ForegroundColor Yellow
    try {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
        Write-Host "Tache existante supprimee avec succes" -ForegroundColor Green
    }
    catch {
        Write-Host "ERREUR lors de la suppression de la tache existante: $_" -ForegroundColor Red
        exit 1
    }
}

# Creer l'action (executer le script Python)
try {
    $action = New-ScheduledTaskAction -Execute $pythonExe -Argument "`"$scriptPath`"" -WorkingDirectory $PSScriptRoot
    
    # Creer le declencheur (tous les jours a 9h00)
    $trigger = New-ScheduledTaskTrigger -Daily -At "09:00"
    
    # Creer les parametres
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    
    # Enregistrer la tache
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description $description -RunLevel Highest -ErrorAction Stop
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Tache planifiee creee avec succes!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Nom de la tache: $taskName" -ForegroundColor Cyan
    Write-Host "Execution: Tous les jours a 9h00" -ForegroundColor Cyan
    Write-Host "Script: $scriptPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Pour gerer la tache:" -ForegroundColor Yellow
    Write-Host "  - Planificateur de taches Windows: taskschd.msc" -ForegroundColor White
    Write-Host "  - Voir la tache: Get-ScheduledTask -TaskName $taskName" -ForegroundColor White
    Write-Host "  - Supprimer la tache: Unregister-ScheduledTask -TaskName $taskName" -ForegroundColor White
}
catch {
    Write-Host ""
    Write-Host "ERREUR lors de la creation de la tache planifiee:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Assurez-vous d'avoir les droits administrateur" -ForegroundColor Yellow
    exit 1
}
