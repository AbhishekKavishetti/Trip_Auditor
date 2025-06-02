@echo off
echo [INFO] Starting documentation generation...

REM Step 1: Navigate to the script's folder
cd /d %~dp0

REM Step 2: Run Doxygen with the Doxyfile in the same folder
doxygen Doxyfile
if errorlevel 1 (
    echo [ERROR] Doxygen failed!
    pause
    exit /b 1
)

REM Step 3: Go to the latex output folder created locally
cd latex

REM Step 4: Compile the LaTeX file twice to resolve references
if not exist refman.tex (
    echo [ERROR] refman.tex not found! Doxygen may have failed to generate LaTeX output.
    pause
    exit /b 1
)
pdflatex refman.tex
pdflatex refman.tex

REM Step 5: Open the final PDF
if exist refman.pdf (
    start refman.pdf
    echo [INFO] Documentation PDF generated successfully.
) else (
    echo [ERROR] PDF not generated!
)
pause
