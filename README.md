# Instrucciones para abrir el notebook

Este directorio contiene `Datasetvinos.ipynb`.

Opciones para abrirlo:

1) Usando VS Code (recomendado)
   - Abre Visual Studio Code.
   - File → Open Folder... → selecciona `c:\Users\Usuario\Desktop\FinalMaster`.
   - Abre `Datasetvinos.ipynb` desde el explorador lateral.
   - Si necesitas ejecutar celdas, instala las extensiones "Python" y "Jupyter" de Microsoft y selecciona el intérprete Python (Ctrl+Shift+P → "Python: Select Interpreter").

2) Usando PowerShell y Jupyter
   - Abre PowerShell.
   - cd "C:\Users\Usuario\Desktop\FinalMaster"
   - (Opcional) Activa tu entorno virtual: `./venv/Scripts/Activate.ps1`
   - Ejecuta: `jupyter notebook` o `jupyter lab`

3) Si no tienes Jupyter instalado:
   - pip install jupyterlab jupyter

Problemas comunes:
- Si PowerShell no permite ejecutar el script de activación del venv, cambia la política de ejecución:
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Si VS Code no muestra kernel, instala las extensiones y selecciona el intérprete.

Archivos incluidos:
- `Datasetvinos.ipynb` — tu notebook.
- `setup_env.ps1` — script para crear y preparar un venv e instalar dependencias.
- `requirements.txt` — dependencias recomendadas.

Si quieres, puedo ejecutar el script `setup_env.ps1` aquí o guiarte paso a paso para ejecutarlo en tu máquina.