@echo off
REM ================================================================
REM commit_extra_credit.bat
REM
REM Commit del Extra Credit (SonarCloud + tests).
REM Requiere que preparar_extra_credit.bat se haya corrido ANTES,
REM Y que hayas editado sonar-project.properties con tus keys reales,
REM Y que hayas configurado el secret SONAR_TOKEN en GitHub.
REM
REM No crea tag (V1.1.1 ya fue creado con Avance 4).
REM ================================================================

setlocal enabledelayedexpansion

echo.
echo ====================================================
echo   COMMIT DEL EXTRA CREDIT (SonarCloud + tests)
echo ====================================================
echo.

if not exist ".git" (
    echo [ERROR] No se detecta repositorio git.
    pause
    exit /b 1
)

REM Advertencia sobre sonar-project.properties
if exist "sonar-project.properties" (
    findstr /C:"ANASTASIA_ORG_KEY_AQUI" sonar-project.properties >nul
    if !errorlevel! equ 0 (
        echo.
        echo [ADVERTENCIA] sonar-project.properties todavia tiene los placeholders!
        echo   ANASTASIA_ORG_KEY_AQUI y ANASTASIA_PROJECT_KEY_AQUI
        echo   Reemplazalos por tus valores reales de SonarCloud antes de continuar.
        echo.
        set /p CONTINUE=Continuar de todos modos? ^(s/N^):
        if /i not "!CONTINUE!"=="s" (
            echo Cancelado. Editar sonar-project.properties y volver a correr.
            pause
            exit /b 0
        )
    )
)

git checkout developer

echo.
echo === Agregando archivos del Extra Credit ===

REM Tests
git add tests\__init__.py
git add tests\test_deploy.py
git add tests\test_ft_engineering.py
git add tests\test_models.py

REM SonarCloud config
git add sonar-project.properties

REM GitHub Action
git add .github\workflows\sonar.yml

REM .gitignore actualizado por preparar_extra_credit.bat
git add .gitignore

echo.
echo Archivos staged:
git status --short

echo.
echo === Creando commit Extra Credit ===
git commit -m "Extra Credit: tests + SonarCloud config + GitHub Actions"

echo.
echo === Sincronizando certification y master ===
git checkout certification
git reset --hard developer
git checkout master
git reset --hard developer
git checkout developer

echo.
echo ====================================================
echo   PUSH A GITHUB
echo ====================================================
echo.
echo Push forzado de las 3 ramas.
echo Si te pide credenciales, usa tu Personal Access Token.
echo.
pause

git push origin master --force
git push origin certification --force
git push origin developer --force

echo.
echo ====================================================
echo   ESTADO FINAL
echo ====================================================
git log --oneline --all --decorate -n 10

echo.
echo ====================================================
echo   TERMINASTE EL EXTRA CREDIT
echo ====================================================
echo.
echo   Repo: https://github.com/anastasiaganderats/mlops_credito_m5
echo.
echo   VERIFICACIONES:
echo.
echo   1. En GitHub ^> Actions: la workflow "SonarCloud Analysis" debe correr
echo      automaticamente. Tarda 3-5 minutos.
echo.
echo   2. Cuando termine con check verde, ir a SonarCloud:
echo      https://sonarcloud.io/project/overview?id=[tu_project_key]
echo      Vas a ver: bugs, vulnerabilities, code smells, coverage.
echo.
echo   3. Si la Action falla con "SONAR_TOKEN not set":
echo      GitHub ^> Settings ^> Secrets and variables ^> Actions ^>
echo      Verificar que existe el secret SONAR_TOKEN.
echo.
echo   PROYECTO COMPLETO.
echo   Repositorio publico listo para entregar.
echo.
pause
