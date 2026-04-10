@echo off
title BEI Dashboard
echo Starting Burn Equity Index Dashboard...
echo.
cd /d "%~dp0"
python serve.py
pause
