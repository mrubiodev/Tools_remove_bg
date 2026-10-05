cd ./.venv/Scripts/
call activate.bat
cd ../..
python -m pip freeze > requirements.txt

pause