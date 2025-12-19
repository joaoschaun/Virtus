"""Script para rodar o servidor."""
import os
import sys

# Define o diretório como o atual
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    # Usa reload=False para evitar erros de import com __file__
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
