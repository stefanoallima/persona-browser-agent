@echo off
REM SUDD Command Sync Script (Windows)
REM Syncs commands from sudd/commands/ to CLI agent folders
REM Also supports update subcommand for updating SUDD framework in target projects

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "SUDD_COMMANDS=%PROJECT_ROOT%\sudd\commands"

REM Parse first argument
if "%~1"=="" goto :do_all
if "%~1"=="opencode" goto :do_oc_only
if "%~1"=="claude" goto :do_cl_only
if "%~1"=="crush" goto :do_cr_only
if "%~1"=="all" goto :do_all
if "%~1"=="update" goto :do_update
echo Usage: %0 [opencode^|claude^|crush^|all^|update ^<target-dir^> [--dry-run] [--force]]
exit /b 1

:do_all
echo [sudd:sync] Syncing SUDD commands...
call :sync_opencode
call :sync_claude
call :sync_crush
echo [sudd:sync] Done!
exit /b 0

:do_oc_only
echo [sudd:sync] Syncing SUDD commands...
call :sync_opencode
echo [sudd:sync] Done!
exit /b 0

:do_cl_only
echo [sudd:sync] Syncing SUDD commands...
call :sync_claude
echo [sudd:sync] Done!
exit /b 0

:do_cr_only
echo [sudd:sync] Syncing SUDD commands...
call :sync_crush
echo [sudd:sync] Done!
exit /b 0

REM ─── Sync to OpenCode CLI ──────────────────────────────────────────────────
:sync_opencode
set "OC_TARGET=%PROJECT_ROOT%\.opencode\command"
if not exist "%OC_TARGET%" mkdir "%OC_TARGET%"

for %%f in ("%SUDD_COMMANDS%\macro\*.md") do (
    copy "%%f" "%OC_TARGET%\sudd-%%~nf.md" >nul
        powershell -Command "(Get-Content '%OC_TARGET%\sudd-%%~nf.md') -replace '^name: sudd:.*', 'name: sudd-%%~nf' | Set-Content '%OC_TARGET%\sudd-%%~nf.md'"
    echo   [OK] opencode: sudd-%%~nf
)
for %%f in ("%SUDD_COMMANDS%\micro\*.md") do (
    copy "%%f" "%OC_TARGET%\sudd-%%~nf.md" >nul
        powershell -Command "(Get-Content '%OC_TARGET%\sudd-%%~nf.md') -replace '^name: sudd:.*', 'name: sudd-%%~nf' | Set-Content '%OC_TARGET%\sudd-%%~nf.md'"
    echo   [OK] opencode: sudd-%%~nf
)
exit /b 0

REM ─── Sync to Claude Code CLI ───────────────────────────────────────────────
:sync_claude
set "CL_TARGET=%PROJECT_ROOT%\.claude\commands\sudd"
if not exist "%CL_TARGET%" mkdir "%CL_TARGET%"

for %%f in ("%SUDD_COMMANDS%\macro\*.md") do (
    copy "%%f" "%CL_TARGET%\%%~nf.md" >nul
    echo   [OK] claude: sudd/%%~nf
)
for %%f in ("%SUDD_COMMANDS%\micro\*.md") do (
    copy "%%f" "%CL_TARGET%\%%~nf.md" >nul
    echo   [OK] claude: sudd/%%~nf
)
exit /b 0

REM ─── Sync to Crush CLI ─────────────────────────────────────────────────────
:sync_crush
set "CR_TARGET=%PROJECT_ROOT%\.crush\commands"
if not exist "%CR_TARGET%" mkdir "%CR_TARGET%"

for %%f in ("%SUDD_COMMANDS%\macro\*.md") do (
    copy "%%f" "%CR_TARGET%\sudd-%%~nf.md" >nul
    powershell -Command "(Get-Content '%CR_TARGET%\sudd-%%~nf.md') -replace '^name: sudd:.*', 'name: sudd-%%~nf' | Set-Content '%CR_TARGET%\sudd-%%~nf.md'"
    echo   [OK] crush: sudd-%%~nf
)
for %%f in ("%SUDD_COMMANDS%\micro\*.md") do (
    copy "%%f" "%CR_TARGET%\sudd-%%~nf.md" >nul
    powershell -Command "(Get-Content '%CR_TARGET%\sudd-%%~nf.md') -replace '^name: sudd:.*', 'name: sudd-%%~nf' | Set-Content '%CR_TARGET%\sudd-%%~nf.md'"
    echo   [OK] crush: sudd-%%~nf
)
exit /b 0

REM ─── Update subcommand ─────────────────────────────────────────────────────
REM Updates the SUDD framework in a target project directory.
REM Overwrites: agents/, commands/, context/, specs/, vision.md, state.schema.json
REM Preserves: personas/, changes/, memory/, state.json, sudd.yaml

:do_update

set "UPDATE_TARGET_DIR=%~2"
set "DRY_RUN=0"
set "FORCE=0"

REM Parse flags
if "%~2"=="--dry-run" (
    set "UPDATE_TARGET_DIR="
    set "DRY_RUN=1"
)
if "%~2"=="--force" (
    set "UPDATE_TARGET_DIR="
    set "FORCE=1"
)
if "%~3"=="--dry-run" set "DRY_RUN=1"
if "%~3"=="--force" set "FORCE=1"

REM Default target to PROJECT_ROOT if not provided
if "%UPDATE_TARGET_DIR%"=="" set "UPDATE_TARGET_DIR=%PROJECT_ROOT%"

REM Verify target directory exists
if not exist "%UPDATE_TARGET_DIR%" (
    echo [ERROR] Target directory does not exist: %UPDATE_TARGET_DIR%
    exit /b 1
)

REM Verify target has sudd/ installed
if not exist "%UPDATE_TARGET_DIR%\sudd" (
    echo [ERROR] SUDD not installed, run "sudd init" first
    exit /b 1
)

set "SOURCE_SUDD=%SCRIPT_DIR%"
set "TARGET_SUDD=%UPDATE_TARGET_DIR%\sudd"

echo [sudd:sync] Updating SUDD framework in: %UPDATE_TARGET_DIR%
if "%DRY_RUN%"=="1" echo [WARN] DRY RUN - no files will be modified

REM Framework dirs and files to overwrite
set "OVERWRITE_DIRS=agents commands context specs"
set "OVERWRITE_FILES=vision.md state.schema.json"

REM Compute diff summary
set "ADDED=0"
set "MODIFIED=0"
set "UNCHANGED=0"
set "TOTAL=0"

REM Count files in overwrite dirs
for %%d in (%OVERWRITE_DIRS%) do (
    if exist "%SOURCE_SUDD%\%%d" (
        for /r "%SOURCE_SUDD%\%%d" %%f in (*) do (
            set /a TOTAL+=1
            set "REL_PATH=%%f"
            set "REL_PATH=!REL_PATH:%SOURCE_SUDD%\=!"
            if not exist "%TARGET_SUDD%\!REL_PATH!" (
                set /a ADDED+=1
            ) else (
                fc /b "%SOURCE_SUDD%\!REL_PATH!" "%TARGET_SUDD%\!REL_PATH!" >nul 2>&1
                if errorlevel 1 (
                    set /a MODIFIED+=1
                ) else (
                    set /a UNCHANGED+=1
                )
            )
        )
    )
)

REM Count individual overwrite files
for %%f in (%OVERWRITE_FILES%) do (
    if exist "%SOURCE_SUDD%\%%f" (
        set /a TOTAL+=1
        if not exist "%TARGET_SUDD%\%%f" (
            set /a ADDED+=1
        ) else (
            fc /b "%SOURCE_SUDD%\%%f" "%TARGET_SUDD%\%%f" >nul 2>&1
            if errorlevel 1 (
                set /a MODIFIED+=1
            ) else (
                set /a UNCHANGED+=1
            )
        )
    )
)

echo.
echo [sudd:sync] Diff summary:
echo   Files to add:      %ADDED%
echo   Files to modify:   %MODIFIED%
echo   Files unchanged:   %UNCHANGED%
echo   Total:             %TOTAL%
echo.

REM Check if nothing to update
if %ADDED%==0 if %MODIFIED%==0 (
    echo [sudd:sync] Nothing to update - framework is already current.
    exit /b 0
)

REM Dry run - show details and exit
if "%DRY_RUN%"=="1" (
    for %%d in (%OVERWRITE_DIRS%) do (
        if exist "%SOURCE_SUDD%\%%d" (
            for /r "%SOURCE_SUDD%\%%d" %%f in (*) do (
                set "REL_PATH=%%f"
                set "REL_PATH=!REL_PATH:%SOURCE_SUDD%\=!"
                if not exist "%TARGET_SUDD%\!REL_PATH!" (
                    echo   + ADD      !REL_PATH!
                ) else (
                    fc /b "%SOURCE_SUDD%\!REL_PATH!" "%TARGET_SUDD%\!REL_PATH!" >nul 2>&1
                    if errorlevel 1 echo   ~ MODIFY   !REL_PATH!
                )
            )
        )
    )
    for %%f in (%OVERWRITE_FILES%) do (
        if exist "%SOURCE_SUDD%\%%f" (
            if not exist "%TARGET_SUDD%\%%f" (
                echo   + ADD      %%f
            ) else (
                fc /b "%SOURCE_SUDD%\%%f" "%TARGET_SUDD%\%%f" >nul 2>&1
                if errorlevel 1 echo   ~ MODIFY   %%f
            )
        )
    )
    echo.
    echo [WARN] Dry run complete. Re-run without --dry-run to apply.
    exit /b 0
)

REM Confirmation prompt (unless --force)
if "%FORCE%"=="0" (
    set /p CONFIRM="Proceed with update? [y/N] "
    if /i not "!CONFIRM!"=="y" (
        echo Update cancelled.
        exit /b 0
    )
)

REM Backup existing framework files
for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value 2^>nul ^| find "="') do set "DT=%%i"
set "TIMESTAMP=%DT:~0,4%%DT:~4,2%%DT:~6,2%_%DT:~8,2%%DT:~10,2%%DT:~12,2%"
set "BACKUP_DIR=%UPDATE_TARGET_DIR%\.sudd-backup\%TIMESTAMP%"

echo [sudd:sync] Backing up to: .sudd-backup\%TIMESTAMP%
for %%d in (%OVERWRITE_DIRS%) do (
    if exist "%TARGET_SUDD%\%%d" (
        xcopy "%TARGET_SUDD%\%%d" "%BACKUP_DIR%\%%d\" /e /i /q >nul 2>&1
    )
)
for %%f in (%OVERWRITE_FILES%) do (
    if exist "%TARGET_SUDD%\%%f" (
        if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
        copy "%TARGET_SUDD%\%%f" "%BACKUP_DIR%\%%f" >nul 2>&1
    )
)
echo   [OK] Backup complete

REM Overwrite framework dirs
for %%d in (%OVERWRITE_DIRS%) do (
    if exist "%SOURCE_SUDD%\%%d" (
        if exist "%TARGET_SUDD%\%%d" rmdir /s /q "%TARGET_SUDD%\%%d"
        xcopy "%SOURCE_SUDD%\%%d" "%TARGET_SUDD%\%%d\" /e /i /q >nul
        echo   [OK] Updated sudd\%%d
    )
)

REM Overwrite framework files
for %%f in (%OVERWRITE_FILES%) do (
    if exist "%SOURCE_SUDD%\%%f" (
        copy "%SOURCE_SUDD%\%%f" "%TARGET_SUDD%\%%f" >nul
        echo   [OK] Updated sudd\%%f
    )
)

REM Write .sudd-version
set "GIT_HASH=manual"
where git >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%h in ('git -C "%SOURCE_SUDD%" rev-parse --short HEAD 2^>nul') do set "GIT_HASH=%%h"
)

set "SUDD_VERSION=3.0.0"
for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value 2^>nul ^| find "="') do set "NOW=%%i"
set "ISO_TS=%NOW:~0,4%-%NOW:~4,2%-%NOW:~6,2%T%NOW:~8,2%:%NOW:~10,2%:%NOW:~12,2%Z"

(
    echo version: %SUDD_VERSION%
    echo source: %GIT_HASH%
    echo updated: %ISO_TS%
) > "%UPDATE_TARGET_DIR%\.sudd-version"

echo   [OK] Wrote .sudd-version
echo.
echo [sudd:sync] Update complete! %ADDED% added, %MODIFIED% modified, %UNCHANGED% unchanged.
exit /b 0
