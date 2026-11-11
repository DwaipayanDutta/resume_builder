@echo off
REM =====================================================================
REM run_resume.bat - tailor a resume to a job and build Resume.docx/.pdf
REM
REM Keep this file inside the extracted resume_builder folder (next to
REM pyproject.toml) and double-click it. Do not run it from inside the zip.
REM The window stays open so any error message can be read.
REM Choices: 1 local Qwen 2.5 3B, 2 Claude API, 3 LiteLLM, 4 format only
REM =====================================================================
if defined RB_CHILD goto :start
set "RB_CHILD=1"
cmd /k ""%~f0""
exit /b

:start
setlocal EnableExtensions
cd /d "%~dp0"
echo Working folder: %CD%
echo.

echo [1/5] Looking for Python...
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if defined PY goto :py_ok
echo [ERROR] Python was not found on PATH.
echo Install Python 3 from https://www.python.org/downloads/
echo and tick the "Add python.exe to PATH" box.
goto :fail

:py_ok
echo Using: %PY%

echo [2/5] Checking the resume_builder package...
%PY% -c "import resume_builder, docx, reportlab, pypdf" >nul 2>nul
if not errorlevel 1 goto :pkg_ok
if exist "pyproject.toml" goto :pkg_install
echo [ERROR] pyproject.toml was not found in this folder.
echo Extract the whole zip first, then run this file from the
echo extracted resume_builder folder.
goto :fail

:pkg_install
echo Installing resume_builder and its libraries - first run only...
%PY% -m pip install --disable-pip-version-check .
if errorlevel 1 goto :pip_fail
goto :pkg_ok

:pip_fail
echo [ERROR] Package install failed. Check your internet connection
echo and the messages above.
goto :fail

:pkg_ok
:menu
echo.
echo ====================================================================
echo How do you want to build your resume?
echo 1. Tailor to a job with LOCAL Qwen 2.5 3B - free, private, offline
echo 2. Tailor to a job with the CLAUDE API - better quality, needs a key
echo 3. Tailor to a job with LiteLLM - 100+ providers, needs a key/model
echo 4. Format my TXT only - no AI
echo ====================================================================
set "CHOICE="
set /p "CHOICE=Choose 1, 2, 3 or 4: "
if "%CHOICE%"=="1" goto :local
if "%CHOICE%"=="2" goto :claude
if "%CHOICE%"=="3" goto :litellm
if "%CHOICE%"=="4" goto :plain
echo Invalid choice.
goto :menu

:local
set "BACKEND=qwen"
echo [3/5] Setting up the local model...
call :ensure_ollama
if errorlevel 1 goto :fail
goto :inputs

:claude
set "BACKEND=claude"
if defined ANTHROPIC_API_KEY goto :inputs
echo.
echo Your key is used for this run only and is not saved to disk.
set /p "ANTHROPIC_API_KEY=Paste your Anthropic API key: "
if defined ANTHROPIC_API_KEY goto :inputs
echo [ERROR] No API key entered.
goto :fail

:litellm
set "BACKEND=litellm"
echo.
echo LiteLLM supports many providers. Set the appropriate API key
echo in your environment first (e.g., OPENAI_API_KEY, GEMINI_API_KEY).
echo You will be asked for a model string later (e.g., gpt-4o,
echo gemini/gemini-2.5-flash, groq/llama-3.3-70b-versatile).
goto :inputs

:plain
set "BACKEND="
goto :inputs

:inputs
echo.
echo Enter the path to your resume TXT file - drag and drop works.
echo Press Enter for the default: examples\New Resume.txt
set "TXT="
set /p "TXT=Resume TXT file: "
if defined TXT set "TXT=%TXT:"=%"
if not defined TXT set "TXT=examples\New Resume.txt"
if exist "%TXT%" goto :txt_ok
echo [ERROR] File not found: "%TXT%"
goto :fail

:txt_ok
set "JOB="
set "COMPANY="
set "JD="
if not defined BACKEND goto :outputs
echo.
set /p "JOB=Target job title: "
if defined JOB set "JOB=%JOB:"=%"
if defined JOB goto :job_ok
echo [ERROR] A job title is required.
goto :fail

:job_ok
set /p "COMPANY=Company - optional: "
if defined COMPANY set "COMPANY=%COMPANY:"=%"
echo.
echo Save the job description in a .txt file, then give its path.
set /p "JD=Job description TXT file: "
if defined JD set "JD=%JD:"=%"
if exist "%JD%" goto :outputs
echo [ERROR] Job description file not found: "%JD%"
goto :fail

:outputs
echo.
set "OUTDIR="
set /p "OUTDIR=Output folder - Enter for current folder: "
if defined OUTDIR set "OUTDIR=%OUTDIR:"=%"
if not defined OUTDIR set "OUTDIR=."
set "BASENAME="
set /p "BASENAME=Output file name without extension - Enter for Resume: "
if not defined BASENAME set "BASENAME=Resume"

echo.
echo [4/5] Building. Local models can take several minutes, please wait...
echo --------------------------------------------------------------------
if not defined BACKEND goto :run_plain

if "%BACKEND%"=="litellm" goto :ask_model
goto :run_tailor

:ask_model
set "MODEL="
set /p "MODEL=Enter LiteLLM model string (e.g., gpt-4o): "
if not defined MODEL (
    echo [ERROR] A model string is required for LiteLLM.
    goto :fail
)
set "MODEL_ARG=--model "%MODEL%""
goto :run_tailor

:run_tailor
%PY% -m resume_builder.tailor "%TXT%" --job-title "%JOB%" --company "%COMPANY%" --jd "%JD%" --backend %BACKEND% %MODEL_ARG% -o "%OUTDIR%" --basename "%BASENAME%" --verify
set "RC=%ERRORLEVEL%"
goto :finish

:run_plain
%PY% -m resume_builder "%TXT%" -o "%OUTDIR%" --basename "%BASENAME%" --verify
set "RC=%ERRORLEVEL%"

:finish
echo.
if not "%RC%"=="0" goto :build_failed
echo [DONE] Look for %BASENAME%.docx and %BASENAME%.pdf in:
echo %OUTDIR%
echo.
pause
exit

:build_failed
echo [FAILED] Exit code %RC%. Read the messages above.
goto :fail

:fail
echo.
echo The window was left open so you can read the messages above.
pause
exit /b 1

REM =====================================================================
REM Subroutine: install Ollama with winget and download Qwen 2.5 3B
REM =====================================================================
:ensure_ollama
set "OLLAMA="
where ollama >nul 2>nul && set "OLLAMA=ollama"
if not defined OLLAMA if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if defined OLLAMA goto :have_ollama
echo Ollama is not installed. Installing it with winget...
where winget >nul 2>nul
if errorlevel 1 goto :manual_ollama
winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not defined OLLAMA where ollama >nul 2>nul && set "OLLAMA=ollama"
if defined OLLAMA goto :have_ollama
:manual_ollama
echo [ERROR] Could not install Ollama automatically.
echo Install it from https://ollama.com/download then run this file again.
exit /b 1

:have_ollama
echo Ollama is available.
REM The model is downloaded on demand by the resume_builder backend,
REM so no explicit download step is needed here.
exit /b 0