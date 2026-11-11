@echo off
REM =====================================================================
REM  run_resume.bat - tailor a resume to a job and build Resume.docx/.pdf
REM
REM  Keep this file inside the extracted resume_builder folder (next to
REM  pyproject.toml) and double-click it. Do not run it from inside the zip.
REM  The window stays open so any error message can be read.
REM  Choices: 1 local Qwen 2.5 3B, 2 Claude API, 3 any provider, 4 format only
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

echo [1/4] Looking for Python...
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if defined PY goto :py_ok
echo [ERROR] Python was not found on PATH.
echo Install Python 3 from https://www.python.org/downloads/ and tick the Add python.exe to PATH box.
goto :fail
:py_ok
echo Using: %PY%

echo [2/4] Checking the resume_builder package...
%PY% -c "import resume_builder, docx, reportlab, pypdf" >nul 2>nul
if not errorlevel 1 goto :pkg_ok
if exist "pyproject.toml" goto :pkg_install
echo [ERROR] pyproject.toml was not found in this folder.
echo Extract the whole zip first, then run this file from the extracted resume_builder folder.
goto :fail
:pkg_install
echo Installing resume_builder and its libraries - first run only...
%PY% -m pip install --disable-pip-version-check .
if errorlevel 1 goto :pip_fail
goto :pkg_ok
:pip_fail
echo [ERROR] Package install failed. Check your internet connection and the messages above.
goto :fail
:pkg_ok

:menu
echo.
echo           -#####=          Resume Builder
echo          -######-          Tailor your resume to any job
echo      +##=   -######:
echo      ####* -######%%...........
echo      ####*######:=#############-   v0.9.0
echo      ####*=##-  =#############-   -------------------------
echo   :*%%= ####*       ....:*:......  Get started
echo   =####%%==+++-       +#####*.
echo    :*####%%=          =%%####+.   ^> 1. tailor-resume (Local Qwen 2.5 3B)
echo     .*####%%=          =%%####+.     2. tailor-resume (Claude API)
echo      .*###*.       .####-=%%####*.    3. tailor-resume (Any Provider - Gemini, OpenAI, Groq, ...)
echo   ....:=%%+:::..   .####:  =%%###-      4. create-resume (Format TXT only)
echo   ############# .*##-.####:   +-
echo   %%%%%%%%%%%%%.*####=####:
echo            .*####%%= .####:
echo            .*####%%= .####:
echo            +%%###%%=  ****:
echo.
echo      view all commands
echo.

REM Using 'choice' for instant selection without pressing Enter
choice /c 1234 /n /m "^> Select an option (1, 2, 3 or 4): "
set "CHOICE=%ERRORLEVEL%"

if "%CHOICE%"=="1" goto :local
if "%CHOICE%"=="2" goto :claude
if "%CHOICE%"=="3" goto :litellm
if "%CHOICE%"=="4" goto :plain
echo Invalid choice.
goto :menu

:local
set "BACKEND=qwen"
echo [3/4] Setting up the local model...
call :ensure_ollama
if errorlevel 1 goto :fail
goto :inputs

:claude
set "BACKEND=claude"
if defined ANTHROPIC_API_KEY goto :inputs
echo.
echo Your key is used for this run only and is not saved to disk.
set /p "ANTHROPIC_API_KEY=^> Paste your Anthropic API key: "
if defined ANTHROPIC_API_KEY goto :inputs
echo [ERROR] No API key entered.
goto :fail

:litellm
set "BACKEND=litellm"
echo.
echo ====================================================================
echo LiteLLM works with 100+ providers. Enter your credentials as
echo   provider:key
echo Examples:
echo   gemini:AIzaSy...
echo   openai:sk-...
echo   anthropic:sk-ant-...
echo   groq:gsk_...
echo   mistral:...
echo   openrouter:sk-or-...
echo ====================================================================
set "LLM_CRED="
set /p "LLM_CRED=^> provider:key: "
if not defined LLM_CRED (
    echo [ERROR] No credentials entered.
    goto :fail
)
set "PROVIDER="
set "APIKEY="
for /f "tokens=1,* delims=:" %%a in ("%LLM_CRED%") do (
    set "PROVIDER=%%a"
    set "APIKEY=%%b"
)
set "PROVIDER=%PROVIDER: =%"
for /f "tokens=* delims= " %%k in ("%APIKEY%") do set "APIKEY=%%k"
if not defined PROVIDER (
    echo [ERROR] Provider name is missing. Use provider:key
    goto :fail
)
if not defined APIKEY (
    echo [ERROR] API key is empty. Use provider:key
    goto :fail
)
call :map_provider_env
if not defined PROVIDER_ENV goto :unknown_provider
call set "%PROVIDER_ENV%=%APIKEY%"
echo Credentials accepted for provider: %PROVIDER% (env: %PROVIDER_ENV%)
goto :ask_model

:unknown_provider
echo [ERROR] Unknown provider: %PROVIDER%
echo Supported providers:
echo   openai  anthropic/claude  gemini/google  groq   mistral
echo   cohere  openrouter         together       deepseek xai
echo   azure   fireworks          perplexity     huggingface replicate
echo To add another provider, edit the :map_provider_env block in this file.
goto :fail

:map_provider_env
set "PROVIDER_ENV="
if /i "%PROVIDER%"=="openai"       set "PROVIDER_ENV=OPENAI_API_KEY"
if /i "%PROVIDER%"=="anthropic"    set "PROVIDER_ENV=ANTHROPIC_API_KEY"
if /i "%PROVIDER%"=="claude"       set "PROVIDER_ENV=ANTHROPIC_API_KEY"
if /i "%PROVIDER%"=="gemini"       set "PROVIDER_ENV=GEMINI_API_KEY"
if /i "%PROVIDER%"=="google"       set "PROVIDER_ENV=GEMINI_API_KEY"
if /i "%PROVIDER%"=="groq"         set "PROVIDER_ENV=GROQ_API_KEY"
if /i "%PROVIDER%"=="mistral"      set "PROVIDER_ENV=MISTRAL_API_KEY"
if /i "%PROVIDER%"=="cohere"       set "PROVIDER_ENV=COHERE_API_KEY"
if /i "%PROVIDER%"=="openrouter"   set "PROVIDER_ENV=OPENROUTER_API_KEY"
if /i "%PROVIDER%"=="together"     set "PROVIDER_ENV=TOGETHER_API_KEY"
if /i "%PROVIDER%"=="deepseek"     set "PROVIDER_ENV=DEEPSEEK_API_KEY"
if /i "%PROVIDER%"=="xai"          set "PROVIDER_ENV=XAI_API_KEY"
if /i "%PROVIDER%"=="azure"        set "PROVIDER_ENV=AZURE_API_KEY"
if /i "%PROVIDER%"=="fireworks"    set "PROVIDER_ENV=FIREWORKS_API_KEY"
if /i "%PROVIDER%"=="perplexity"   set "PROVIDER_ENV=PERPLEXITY_API_KEY"
if /i "%PROVIDER%"=="huggingface"  set "PROVIDER_ENV=HUGGINGFACE_API_KEY"
if /i "%PROVIDER%"=="replicate"    set "PROVIDER_ENV=REPLICATE_API_KEY"
exit /b

:ask_model
echo.
echo Enter the LiteLLM model string. The provider prefix must match.
echo   Gemini   -^> gemini/gemini-2.5-flash
echo   OpenAI   -^> openai/gpt-4o
echo   Anthropic-^> anthropic/claude-3-5-sonnet-20241022
echo   Groq     -^> groq/llama-3.3-70b-versatile
set "MODEL="
set /p "MODEL=^> Model: "
if not defined MODEL (
    echo [ERROR] A model string is required.
    goto :fail
)
set "MODEL_ARG=--model "%MODEL%""
goto :inputs

:plain
set "BACKEND="
goto :inputs

:inputs
echo.
echo Enter the path to your resume TXT file - drag and drop works.
echo Press Enter for the default: examples\New Resume.txt
set "TXT="
set /p "TXT=^> Resume TXT file: "
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
set /p "JOB=^> Target job title: "
if defined JOB set "JOB=%JOB:"=%"
if defined JOB goto :job_ok
echo [ERROR] A job title is required.
goto :fail
:job_ok
set /p "COMPANY=^> Company - optional: "
if defined COMPANY set "COMPANY=%COMPANY:"=%"
echo.
echo Save the job description in a .txt file, then give its path.
set /p "JD=^> Job description TXT file: "
if defined JD set "JD=%JD:"=%"
if exist "%JD%" goto :outputs
echo [ERROR] Job description file not found: "%JD%"
goto :fail

:outputs
echo.
set "OUTDIR="
set /p "OUTDIR=^> Output folder - Enter for current folder: "
if defined OUTDIR set "OUTDIR=%OUTDIR:"=%"
if not defined OUTDIR set "OUTDIR=."
set "BASENAME="
set /p "BASENAME=^> Output file name without extension - Enter for Resume: "
if not defined BASENAME set "BASENAME=Resume"

echo.
echo [4/4] Building. Local models can take several minutes, please wait...
echo --------------------------------------------------------------------
if not defined BACKEND goto :run_plain
%PY% -m resume_builder.tailor "%TXT%" --job-title "%JOB%" --company "%COMPANY%" --jd "%JD%" --backend %BACKEND% %MODEL_ARG% -o "%OUTDIR%" --basename "%BASENAME%" --verify
set "RC=%ERRORLEVEL%"
goto :finish
:run_plain
%PY% -m resume_builder "%TXT%" -o "%OUTDIR%" --basename "%BASENAME%" --verify
set "RC=%ERRORLEVEL%"

:finish
echo.
if not "%RC%"=="0" goto :build_failed
echo [DONE] Look for %BASENAME%.docx and %BASENAME%.pdf in: %OUTDIR%
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
REM  Subroutine: install Ollama with winget and download Qwen 2.5 3B
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
"%OLLAMA%" list >nul 2>nul
if not errorlevel 1 goto :ollama_up
echo Starting the Ollama server...
start "Ollama server" /min "%OLLAMA%" serve
set /a TRIES=0
:wait_ollama
timeout /t 2 /nobreak >nul
"%OLLAMA%" list >nul 2>nul
if not errorlevel 1 goto :ollama_up
set /a TRIES+=1
if %TRIES% LSS 20 goto :wait_ollama
echo [ERROR] The Ollama server did not start.
exit /b 1

:ollama_up
"%OLLAMA%" list | findstr /i /c:"qwen2.5:3b" >nul
if not errorlevel 1 goto :model_ready
echo Downloading Qwen 2.5 3B - about 2 GB, one time only...
"%OLLAMA%" pull qwen2.5:3b
if errorlevel 1 goto :pull_failed
goto :model_ready
:pull_failed
echo [ERROR] Model download failed. Check your internet connection.
exit /b 1
:model_ready
echo Local model ready: qwen2.5:3b
exit /b 0