@echo off
set PYTHONIOENCODING=utf-8
echo Starting DpBoss RAG Guessing Studio...
".\python_env\python.exe" -m streamlit run src\app.py
pause
