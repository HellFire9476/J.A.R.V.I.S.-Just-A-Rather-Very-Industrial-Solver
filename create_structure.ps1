
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$directories = @(
    "docs",
    "assets/icons/navigation",
    "assets/icons/resources",
    "assets/icons/buildings",
    "assets/icons/status",
    "assets/illustrations",
    "assets/fonts",
    "assets/licenses",
    "resources/styles",
    "resources/schemas",

    "src/jarvis/app",
    "src/jarvis/config",
    "src/jarvis/presentation/pages/dashboard",
    "src/jarvis/presentation/pages/parks",
    "src/jarvis/presentation/pages/factories",
    "src/jarvis/presentation/pages/extraction",
    "src/jarvis/presentation/pages/energy",
    "src/jarvis/presentation/pages/network",
    "src/jarvis/presentation/pages/recipes",
    "src/jarvis/presentation/pages/simulations",
    "src/jarvis/presentation/widgets",
    "src/jarvis/presentation/dialogs",
    "src/jarvis/domain/entities",
    "src/jarvis/domain/value_objects",
    "src/jarvis/engines",
    "src/jarvis/application/services",
    "src/jarvis/infrastructure/persistence",
    "src/jarvis/infrastructure/catalog",
    "src/jarvis/infrastructure/logging",

    "tests/unit",
    "tests/integration",
    "tests/fixtures",
    "tools"
)

$files = @(
    "README.md",
    "pyproject.toml",
    ".gitignore",
    "docs/architecture.md",
    "docs/data_format.md",
    "docs/ui_guidelines.md",
    "assets/licenses/THIRD_PARTY_LICENSES.md",

    "resources/styles/main.qss",
    "resources/schemas/project.schema.json",
    "resources/schemas/park.schema.json",
    "resources/schemas/factory.schema.json",
    "resources/schemas/scenario.schema.json",

    "src/jarvis/__init__.py",
    "src/jarvis/__main__.py",
    "src/jarvis/bootstrap.py",

    "src/jarvis/app/application.py",
    "src/jarvis/app/main_window.py",
    "src/jarvis/app/navigation.py",

    "src/jarvis/config/settings.py",
    "src/jarvis/config/paths.py",

    "src/jarvis/presentation/pages/dashboard/page.py",
    "src/jarvis/presentation/pages/parks/page.py",
    "src/jarvis/presentation/pages/parks/park_details.py",
    "src/jarvis/presentation/pages/factories/page.py",
    "src/jarvis/presentation/pages/extraction/page.py",
    "src/jarvis/presentation/pages/energy/page.py",
    "src/jarvis/presentation/pages/network/page.py",
    "src/jarvis/presentation/pages/recipes/page.py",
    "src/jarvis/presentation/pages/simulations/page.py",

    "src/jarvis/presentation/widgets/sidebar.py",
    "src/jarvis/presentation/widgets/header.py",
    "src/jarvis/presentation/widgets/metric_card.py",
    "src/jarvis/presentation/widgets/status_badge.py",
    "src/jarvis/presentation/widgets/view_selector.py",

    "src/jarvis/presentation/dialogs/park_dialog.py",
    "src/jarvis/presentation/dialogs/factory_dialog.py",
    "src/jarvis/presentation/dialogs/machine_dialog.py",

    "src/jarvis/domain/entities/project.py",
    "src/jarvis/domain/entities/park.py",
    "src/jarvis/domain/entities/factory.py",
    "src/jarvis/domain/entities/machine.py",
    "src/jarvis/domain/entities/resource_node.py",
    "src/jarvis/domain/entities/extractor.py",
    "src/jarvis/domain/entities/generator.py",
    "src/jarvis/domain/entities/power_grid.py",
    "src/jarvis/domain/entities/transfer.py",
    "src/jarvis/domain/entities/scenario.py",

    "src/jarvis/domain/value_objects/identifiers.py",
    "src/jarvis/domain/value_objects/units.py",
    "src/jarvis/domain/value_objects/enums.py",

    "src/jarvis/engines/production_engine.py",
    "src/jarvis/engines/extraction_engine.py",
    "src/jarvis/engines/energy_engine.py",
    "src/jarvis/engines/network_engine.py",
    "src/jarvis/engines/deficit_analyzer.py",
    "src/jarvis/engines/simulation_engine.py",

    "src/jarvis/application/services/project_service.py",
    "src/jarvis/application/services/park_service.py",
    "src/jarvis/application/services/factory_service.py",
    "src/jarvis/application/services/catalog_service.py",
    "src/jarvis/application/services/simulation_service.py",

    "src/jarvis/infrastructure/persistence/json_store.py",
    "src/jarvis/infrastructure/persistence/project_repository.py",
    "src/jarvis/infrastructure/persistence/catalog_repository.py",
    "src/jarvis/infrastructure/persistence/atomic_writer.py",
    "src/jarvis/infrastructure/persistence/backup_manager.py",

    "src/jarvis/infrastructure/catalog/satisfactory_importer.py",
    "src/jarvis/infrastructure/catalog/catalog_parser.py",
    "src/jarvis/infrastructure/logging/logging_config.py",

    "tests/conftest.py",
    "tools/inspect_game_data.py",
    "tools/validate_catalog.py"
)

# Creation des dossiers
foreach ($directory in $directories) {
    New-Item -ItemType Directory -Path $directory -Force |
        Out-Null
}

# Creation des fichiers sans ecraser les fichiers existants
foreach ($file in $files) {
    $parent = Split-Path $file -Parent

    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force |
            Out-Null
    }

    if (-not (Test-Path $file)) {
        New-Item -ItemType File -Path $file |
            Out-Null
    }
}

# Fichiers d'initialisation Python
$pythonDirectories = @(
    "src/jarvis",
    "src/jarvis/app",
    "src/jarvis/config",
    "src/jarvis/presentation",
    "src/jarvis/presentation/pages",
    "src/jarvis/presentation/pages/dashboard",
    "src/jarvis/presentation/pages/parks",
    "src/jarvis/presentation/pages/factories",
    "src/jarvis/presentation/pages/extraction",
    "src/jarvis/presentation/pages/energy",
    "src/jarvis/presentation/pages/network",
    "src/jarvis/presentation/pages/recipes",
    "src/jarvis/presentation/pages/simulations",
    "src/jarvis/presentation/widgets",
    "src/jarvis/presentation/dialogs",
    "src/jarvis/domain",
    "src/jarvis/domain/entities",
    "src/jarvis/domain/value_objects",
    "src/jarvis/engines",
    "src/jarvis/application",
    "src/jarvis/application/services",
    "src/jarvis/infrastructure",
    "src/jarvis/infrastructure/persistence",
    "src/jarvis/infrastructure/catalog",
    "src/jarvis/infrastructure/logging"
)

foreach ($directory in $pythonDirectories) {
    $initFile = Join-Path $directory "__init__.py"

    if (-not (Test-Path $initFile)) {
        New-Item -ItemType File -Path $initFile |
            Out-Null
    }
}

# Configuration Git
@'
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.env
.idea/
.vscode/
.pytest_cache/
.ruff_cache/
dist/
build/

# Donnees personnelles
user_data/
saves/
backups/
logs/
'@ | Set-Content -Path ".gitignore" -Encoding UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " J.A.R.V.I.S. 2.0" -ForegroundColor Yellow
Write-Host " Architecture creee avec succes !" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Dossiers crees : $($directories.Count)"
Write-Host "Fichiers crees : $($files.Count)"
Write-Host ""
Write-Host "La structure est prete." -ForegroundColor Green
