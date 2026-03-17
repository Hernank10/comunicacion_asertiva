#!/bin/bash
echo "🧹 Limpiando sistema para Git..."

# Limpiar cachés
pip cache purge
rm -rf ~/.cache/pip
rm -rf /tmp/*

# Eliminar archivos compilados
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete

# Comprimir JSON si son muy grandes
if [ -f "data/ejercicios.json" ]; then
    echo "📦 Comprimiendo ejercicios.json..."
    gzip data/ejercicios.json
fi

if [ -f "data/flashcards.json" ]; then
    echo "📦 Comprimiendo flashcards.json..."
    gzip data/flashcards.json
fi

# Ver espacio liberado
echo "✅ Espacio después de limpieza:"
df -h .
du -sh * | sort -h
