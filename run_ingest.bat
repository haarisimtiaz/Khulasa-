@echo off
REM Runs ingest.py and logs the result. Meant to be triggered by
REM Windows Task Scheduler every 30-60 minutes.

cd /d "%~dp0"
echo ==== Ingest run: %DATE% %TIME% ==== >> ingest_log.txt
py ingest.py >> ingest_log.txt 2>&1
echo. >> ingest_log.txt
