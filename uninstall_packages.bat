@echo off
for /f "delims==" %%i in (requirements.txt) do pip uninstall -y %%i
