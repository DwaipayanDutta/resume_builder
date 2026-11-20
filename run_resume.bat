@echo off
REM =====================================================================
REM run_resume.bat - tailor a resume to a job and build Resume.docx/.pdf
REM =====================================================================
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
echo 2. Tailor to a job with ANY PROVIDER - Claude, Gemini, OpenAI, Groq, ...
echo 3. Format my TXT only - no AI
echo 4. Open the WEB APP in your browser - upload TXT, paste a job link,
echo    download the PDF (recommended)
echo ====================================================================
set "CHOICE="
set "WEB="
set /p "CHOICE=Choose 1, 2, 3 or 4: "
if "%CHOICE%"=="1" goto :local
if "%CHOICE%"=="2" goto :litellm
if "%CHOICE%"=="3" goto :plain
if "%CHOICE%"=="4" goto :webapp
echo Invalid choice.
goto :menu

:webapp
set "WEB=1"
echo.
echo ====================================================================
echo Which AI should the web app use for tailoring?
echo 1. LOCAL Qwen 2.5 3B - free, private, offline
echo 2. ANY PROVIDER - Claude, Gemini, OpenAI, Groq, ...
echo 3. No AI - format my TXT only
echo You can still choose "Format only" inside the app at any time.
echo ====================================================================
set "WCHOICE="
set /p "WCHOICE=Choose 1, 2 or 3: "
if "%WCHOICE%"=="1" goto :local
if "%WCHOICE%"=="2" goto :litellm
if "%WCHOICE%"=="3" goto :plain
echo Invalid choice.
goto :webapp

:local
set "BACKEND=qwen"
echo [3/5] Setting up the local model...
call :ensure_ollama
if errorlevel 1 goto :fail
goto :inputs

:litellm
set "BACKEND=litellm"
echo.
echo ====================================================================
echo LiteLLM works with 100+ providers, including Claude. Enter your
echo credentials as
echo   provider:key
echo Your key is used for this run only and is not saved to disk.
echo Examples:
echo   anthropic:sk-ant-...   (Claude)
echo   gemini:AIzaSy...
echo   openai:sk-...
echo   groq:gsk_...
echo   mistral:...
echo   openrouter:sk-or-...
echo ====================================================================
set "LLM_CRED="
set /p "LLM_CRED=provider:key: "
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
echo   Claude   -^> anthropic/claude-sonnet-5-5
echo   Gemini   -^> gemini/gemini-2.5-flash
echo   OpenAI   -^> openai/gpt-4o
echo   Groq     -^> groq/llama-3.3-70b-versatile
set "MODEL="
set /p "MODEL=Model: "
if not defined MODEL (
    echo [ERROR] A model string is required.
    goto :fail
)
set "MODEL_ARG=--model "%MODEL%""
%PY% -c "import litellm" >nul 2>nul
if not errorlevel 1 goto :inputs
echo Installing LiteLLM - first run only...
%PY% -m pip install --disable-pip-version-check ".[ai]"
if errorlevel 1 goto :pip_fail
goto :inputs

:plain
set "BACKEND="
goto :inputs

:inputs
if defined WEB goto :web_start
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
exit /b 0

:build_failed
echo [FAILED] Exit code %RC%. Read the messages above.
goto :fail

:fail
echo.
echo The window was left open so you can read the messages above.
pause
exit /b 1

REM =====================================================================
REM Web app: install web extras, build the UI if needed, start the server
REM and open the browser. API keys stay in this window's environment.
REM =====================================================================
:web_start
set "RESUME_BACKEND=%BACKEND%"
set "RESUME_MODEL=%MODEL%"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
echo.
echo [3/5] Checking web app libraries...
set "EXTRAS=web"
if "%BACKEND%"=="litellm" set "EXTRAS=web,ai"
%PY% -c "import fastapi, uvicorn, multipart, jinja2, httpx, pydantic" >nul 2>nul
if errorlevel 1 goto :web_pip
if not "%BACKEND%"=="litellm" goto :web_ui
%PY% -c "import litellm" >nul 2>nul
if not errorlevel 1 goto :web_ui
:web_pip
echo Installing web app libraries - first run only...
%PY% -m pip install --disable-pip-version-check ".[%EXTRAS%]"
if errorlevel 1 goto :pip_fail

:web_ui
echo [4/5] Checking the web interface...
%PY% -m resume_builder.webapp --check-ui "%CD%\web"
if not errorlevel 1 goto :web_run
call :ensure_node
if errorlevel 1 goto :fail
echo Building the web interface - first run only, takes about a minute...
pushd web
call npm install --no-audit --no-fund
if errorlevel 1 goto :npm_fail
call npm run build
if errorlevel 1 goto :npm_fail
popd
goto :web_run

:npm_fail
popd
echo [ERROR] Building the web interface failed. Read the messages above.
goto :fail

:web_run
echo [5/5] Starting Resume Studio. Your browser will open automatically.
%PY% -m resume_builder.webapp
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" exit /b 0
echo [FAILED] The web app stopped with exit code %RC%.
goto :fail

REM =====================================================================
REM Subroutine: make sure Node.js (npm) is available, install with winget
REM =====================================================================
:ensure_node
REM No ( ) blocks here: a PATH containing "(x86)" would break them.
where npm >nul 2>nul && exit /b 0
if exist "%ProgramFiles%\nodejs\npm.cmd" goto :node_path
echo Node.js is needed once to build the web interface. Installing it with winget...
where winget >nul 2>nul
if errorlevel 1 goto :manual_node
winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
if exist "%ProgramFiles%\nodejs\npm.cmd" goto :node_path
goto :manual_node
:node_path
set "PATH=%ProgramFiles%\nodejs;%PATH%"
exit /b 0
:manual_node
echo [ERROR] Could not install Node.js automatically.
echo Install the LTS version from https://nodejs.org then run this file again.
exit /b 1

REM =====================================================================
REM Subroutine: install Ollama with winget if missing
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
