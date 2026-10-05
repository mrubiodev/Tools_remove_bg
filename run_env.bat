@echo off
echo Activando environment..
:: Agrega aqui las acciones que deseas realizar en el CMD
cd ./.venv/Scripts/
call activate.bat
cd ../..

:espera
echo Esperando mas instrucciones. Para salir, escribe "exit".
set /p instruccion="> "

if /i "%instruccion%"=="exit" goto fin
:: Agrega aqui mas instrucciones según tus necesidades

:: Ejecuta la instruccion y muestra su salida
echo.
echo Resultado de la instruccion "%instruccion%":
%instruccion%
echo.

goto espera

:fin
echo Saliendo del script.