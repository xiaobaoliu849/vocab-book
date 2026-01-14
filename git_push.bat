@echo off
setlocal enabledelayedexpansion

echo [Git Push Script] Starting...

:: 1. Check for git
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH.
    pause
    exit /b 1
)

:: 2. Add all changes
echo Adding changes...
git add .

:: 3. Commit with message
set "commit_msg=UI optimization and branding unification %date% %time%"
echo Committing with message: "%commit_msg%"
git commit -m "%commit_msg%"

:: 4. Push to remote
echo Pushing to GitHub...
git push origin main

if %errorlevel% EQU 0 (
    echo [SUCCESS] Changes pushed to GitHub.
) else (
    echo [ERROR] Failed to push changes. Please check your internet connection or credentials.
)

pause
