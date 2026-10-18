@echo off
title IndexLens Full-Stack Agent
echo =====================================================
echo          IndexLens — Starting Full-Stack Agent       
echo =====================================================

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m src.cli launch %*
) else (
    python -m src.cli launch %*
)
