@echo off
REM =====================================================================
REM  run_resume.bat - build Resume.docx and Resume.pdf from a TXT file.
REM
REM  Keep this .bat file in the resume_builder project folder (next to
REM  pyproject.toml), then double-click it (or run it from cmd).
REM
REM  It will:
REM    1. change to the folder containing this .bat file
REM    2. check Python is available
REM    3. install the required packages if they are missing
REM    4. ask you for the TXT file path (drag-and-drop or paste)
REM    5. run resume_builder --verify
REM    6. pause so you can read the output
REM =====================================================================

setlocal EnableExtensions EnableDelayedExpansion

REM --- 1. always work from the folder that contains this .bat -------------
cd /d "%~dp0"
echo Working folder: %CD%
echo.

REM --- 2. locate Python ---------------------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python was not found on PATH.
    echo Install Python 3 from https://www.python.org/downloads/ and
    echo make sure "Add python.exe to PATH" is ticked during install.
    echo.
    pause
    exit /b 1
)

REM --- 3. make sure the resume_builder package is installed -------------
%PY% -c "import resume_builder" >nul 2>nul
if errorlevel 1 (
    if not exist "pyproject.toml" (
        echo [ERROR] pyproject.toml was not found in:
        echo         %CD%
        echo Put this .bat file in the resume_builder project folder.
        echo.
        pause
        exit /b 1
    )
    echo Installing resume_builder package...
    %PY% -m pip install --quiet --disable-pip-version-check .
    if errorlevel 1 (
        echo [ERROR] package install failed. Run manually:  %PY% -m pip install .
        echo.
        pause
        exit /b 1
    )
)

REM --- 4. verify / install dependencies ----------------------------------
%PY% -c "import docx, reportlab, pypdf" >nul 2>nul
if errorlevel 1 (
    echo Installing required packages: python-docx reportlab pypdf
    %PY% -m pip install --quiet --disable-pip-version-check python-docx reportlab pypdf
    if errorlevel 1 (
        echo [ERROR] pip install failed. Check your internet connection or
        echo         run this manually:  %PY% -m pip install python-docx reportlab pypdf
        echo.
        pause
        exit /b 1
    )
)

REM --- 5. ask the user for the TXT file path -----------------------------
echo.
echo ====================================================================
echo  Enter the path to your resume TXT file.
echo  You can drag-and-drop the file onto this window, or paste the path.
echo  Press Enter with no input to use the default:
echo      examples\New Resume.txt
echo ====================================================================
echo.
set "TXT="
set /p "TXT=Resume TXT file: "

REM strip surrounding double quotes if the user pasted a quoted path
if defined TXT set "TXT=%TXT:"=%"

if not defined TXT set "TXT=examples\New Resume.txt"

if not exist "%TXT%" (
    echo.
    echo [ERROR] File not found: "%TXT%"
    echo.
    pause
    exit /b 1
)

REM --- 6. optional output folder (defaults to this folder) ---------------
echo.
set "OUTDIR="
set /p "OUTDIR=Output folder [Enter for current folder]: "
if defined OUTDIR set "OUTDIR=%OUTDIR:"=%"
if not defined OUTDIR set "OUTDIR=."

REM --- 7. optional output basename ---------------------------------------
echo.
set "BASENAME="
set /p "BASENAME=Output file name without extension [Enter for Resume]: "
if not defined BASENAME set "BASENAME=Resume"

REM --- 8. run the generator with --verify --------------------------------
echo.
echo --------------------------------------------------------------------
echo  Running:  %PY% -m resume_builder "%TXT%" -o "%OUTDIR%" --basename "%BASENAME%" --verify
echo --------------------------------------------------------------------
echo.
%PY% -m resume_builder "%TXT%" -o "%OUTDIR%" --basename "%BASENAME%" --verify
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [DONE] Resume built successfully.
    echo        Look for "%BASENAME%.docx" and "%BASENAME%.pdf" in:
    echo        %OUTDIR%
) else (
    echo [FAILED] resume_builder exited with code %RC%.
    echo          Read the messages above for details.
)

echo.
pause
endlocal
exit /b %RC%