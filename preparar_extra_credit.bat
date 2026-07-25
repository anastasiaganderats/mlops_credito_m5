@echo off
REM ================================================================
REM preparar_extra_credit.bat
REM
REM Devuelve del stash a la carpeta PI los archivos del Extra Credit:
REM   - tests/ (test_deploy.py, test_ft_engineering.py, test_models.py, __init__.py)
REM   - sonar-project.properties
REM   - .github/workflows/sonar.yml
REM
REM IMPORTANTE: antes del commit, tenes que editar sonar-project.properties
REM con tu organization key y project key reales de SonarCloud.
REM ================================================================

setlocal enabledelayedexpansion

REM Detectar automaticamente la carpeta stash. Prueba 3 ubicaciones comunes.
set "STASH="
if exist "%USERPROFILE%\Desktop\PI_stash_futuros_avances" set "STASH=%USERPROFILE%\Desktop\PI_stash_futuros_avances"
if exist "%USERPROFILE%\OneDrive\Escritorio\PI_stash_futuros_avances" set "STASH=%USERPROFILE%\OneDrive\Escritorio\PI_stash_futuros_avances"
if exist "%USERPROFILE%\OneDrive\Desktop\PI_stash_futuros_avances" set "STASH=%USERPROFILE%\OneDrive\Desktop\PI_stash_futuros_avances"

echo.
echo ====================================================
echo   RECUPERANDO ARCHIVOS DEL EXTRA CREDIT
echo ====================================================
echo.

if "%STASH%"=="" (
    echo [ERROR] No se encontro la carpeta PI_stash_futuros_avances en:
    echo   %USERPROFILE%\Desktop\
    echo   %USERPROFILE%\OneDrive\Escritorio\
    echo   %USERPROFILE%\OneDrive\Desktop\
    echo.
    echo Verifica donde tenes el stash y ajustar la variable STASH manualmente en el .bat
    pause
    exit /b 1
)

echo Stash origen: %STASH%
echo Destino: carpeta actual PI
echo.

REM ==== TESTS ====
echo === Restaurando tests\ ===
if not exist "tests" mkdir tests
for %%F in (__init__.py test_deploy.py test_ft_engineering.py test_models.py) do (
    if exist "%STASH%\tests\%%F" (
        copy /Y "%STASH%\tests\%%F" "tests\%%F" >nul
        if !errorlevel! equ 0 (
            del /Q "%STASH%\tests\%%F"
            echo   [OK] tests\%%F
        )
    )
)

REM ==== SONAR PROJECT PROPERTIES ====
echo.
echo === Restaurando sonar-project.properties ===
if exist "%STASH%\sonar-project.properties" (
    copy /Y "%STASH%\sonar-project.properties" "sonar-project.properties" >nul
    if !errorlevel! equ 0 (
        del /Q "%STASH%\sonar-project.properties"
        echo   [OK] sonar-project.properties
    )
)

REM ==== GITHUB ACTIONS WORKFLOW ====
echo.
echo === Restaurando .github\workflows\sonar.yml ===
if not exist ".github\workflows" mkdir ".github\workflows"
if exist "%STASH%\.github\workflows\sonar.yml" (
    copy /Y "%STASH%\.github\workflows\sonar.yml" ".github\workflows\sonar.yml" >nul
    if !errorlevel! equ 0 (
        del /Q "%STASH%\.github\workflows\sonar.yml"
        echo   [OK] .github\workflows\sonar.yml
    )
)

REM ==== ACTUALIZAR .gitignore (quitar las lineas de tests/sonar) ====
echo.
echo === Actualizando .gitignore ===
(
echo # Python
echo __pycache__/
echo *.py[cod]
echo *$py.class
echo *.so
echo.
echo # Entornos virtuales
echo *-venv/
echo venv/
echo env/
echo ENV/
echo .venv
echo.
echo # Jupyter
echo .ipynb_checkpoints/
echo.
echo # ==== TUS DOCUMENTOS PERSONALES ====
echo Guia_*.docx
echo Reporte_*.docx
echo Instrucciones_*.docx
echo Consignas *.docx
echo Consignas*.docx
echo Rubrica *.xlsx
echo Rubrica*.xlsx
echo Base_de_datos.xlsx
echo.
echo # Scripts personales de workflow
echo preparar_avance_*.bat
echo commit_avance_*.bat
echo preparar_extra_*.bat
echo commit_extra_*.bat
echo init_git_avance_*.bat
echo init_git_v2.bat
echo init_git.bat
echo.
echo # Preserva .gitkeep
echo !models/.gitkeep
echo !data_processed/.gitkeep
echo !streamlit_app/.gitkeep
echo !tests/.gitkeep
echo !.github/workflows/.gitkeep
echo.
echo # IDE
echo .vscode/
echo .idea/
echo *.swp
echo .DS_Store
echo.
echo # Logs
echo *.log
echo logs/
echo.
echo # Testing runtime (no van al repo, pero pytest si)
echo .coverage
echo .coverage.*
echo htmlcov/
echo .pytest_cache/
echo coverage.xml
echo pytest-report.xml
echo.
echo # Docker
echo *.tar
echo.
echo # SonarCloud runtime
echo .scannerwork/
echo .sonar/
echo.
echo # OneDrive
echo Thumbs.db
echo desktop.ini
echo.
echo # Temporales
echo image*.png
echo *.tmp
) > .gitignore
echo   [OK] .gitignore actualizado

echo.
echo ====================================================
echo   LISTO. AHORA HAY QUE HACER 3 COSAS ANTES DEL COMMIT:
echo ====================================================
echo.
echo   1. REGISTRAR EL REPO EN SONARCLOUD
echo      - Ir a https://sonarcloud.io
echo      - Log in with GitHub
echo      - "+" ^> Analyze new project ^> seleccionar mlops_credito_m5
echo      - Anotar tu organization key y project key
echo.
echo   2. EDITAR sonar-project.properties
echo      - Reemplazar ANASTASIA_ORG_KEY_AQUI por tu organization key
echo      - Reemplazar ANASTASIA_PROJECT_KEY_AQUI por tu project key
echo.
echo   3. CREAR EL SECRET SONAR_TOKEN EN GITHUB
echo      - En SonarCloud te dio un token (SONAR_TOKEN)
echo      - En GitHub ir a tu repo ^> Settings ^> Secrets and variables ^> Actions
echo      - "New repository secret"
echo      - Name: SONAR_TOKEN, Value: [el token de SonarCloud]
echo.
echo   Cuando termines los 3 pasos, correr: commit_extra_credit.bat
echo.
pause
