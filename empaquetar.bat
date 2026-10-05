IF EXIST "./build/" RMDIR /S /Q "./build/"
IF EXIST "./dist/" RMDIR /S /Q "./dist/"
cd ./.venv/Scripts/
call activate.bat
cd ../..
pyinstaller -i ".\res\app_icon.ico" --noconsole main.py --onefile

if exist ".\dist\" (
    REM Actualizar el archivo de requisitos si la carpeta dist existe
    echo Actualizando el archivo de requisitos...
    pip freeze > requirements.txt
    echo Archivo de requisitos actualizado exitosamente.

    echo Copiando el archivo de requisitos a la carpeta dist...
    copy requirements.txt ".\dist\"
    echo Archivo de requisitos copiado exitosamente.

    if exist "resources_release\" (
        echo Ambas carpetas existen. Copiando archivos...
        xcopy /E /I /Y  "resources_release\" ".\dist\"
        echo Archivos copiados exitosamente.
    ) else (
        echo La carpeta "./dist/" existe, pero la carpeta "resources_release" no.
    )
) else (
    if exist "resources_release\" (
        echo La carpeta "./dist/" no existe, pero la carpeta "resources_release" si.
    ) else (
        echo Ninguna de las dos carpetas existe.
    )
)


pause