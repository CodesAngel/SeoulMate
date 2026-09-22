$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$Streamlit = if (Test-Path ".\.venv\Scripts\streamlit.exe") { ".\.venv\Scripts\streamlit.exe" } else { "streamlit" }
& $Streamlit run frontend\streamlit_app.py
