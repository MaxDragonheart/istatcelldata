#!/usr/bin/env bash
#
# Script di verifica locale pre-rilascio per il progetto istat-census-data:
# - controlla versione e tag
# - installa/aggiorna le dipendenze
# - esegue opzionalmente i test
# - costruisce gli artifact locali
#
# La pubblicazione su PyPI avviene da GitHub Actions tramite PyPI Trusted
# Publishing, non da questo script.
#
# Uso:
#   ./release.sh
#   RUN_TESTS=1 ./release.sh     # per eseguire i test prima della build
#

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "🔎 Verifica presenza pyproject.toml..."
if [[ ! -f "pyproject.toml" ]]; then
  echo "❌ Errore: pyproject.toml non trovato in $PROJECT_ROOT"
  exit 1
fi

# -------------------------------------------------------------
# 1️⃣ Estrarre versione da pyproject.toml
# -------------------------------------------------------------
echo "📄 Lettura versione da pyproject.toml..."
PACKAGE_NAME=$(python3 - << 'EOF'
import tomllib, pathlib
data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
print(data["tool"]["poetry"]["name"])
EOF
)

VERSION=$(python3 - << 'EOF'
import tomllib, pathlib
data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
print(data["tool"]["poetry"]["version"])
EOF
)

echo "📦 Distribuzione PyPI: $PACKAGE_NAME"
echo "📦 Versione trovata: $VERSION"

# -------------------------------------------------------------
# 2️⃣ Verificare che esista un tag git corrispondente
# -------------------------------------------------------------
echo "🔍 Controllo tag git corrispondente..."

if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    TAG="v$VERSION"
elif git rev-parse "$VERSION" >/dev/null 2>&1; then
    TAG="$VERSION"
else
    echo "❌ Nessun tag git trovato per la versione $VERSION"
    echo ""
    echo "💡 Crea un tag prima di rilasciare:"
    echo "   git tag v$VERSION"
    echo "   git push origin v$VERSION"
    exit 1
fi

echo "✅ Trovato tag git corretto: $TAG"

# -------------------------------------------------------------
# 3️⃣ Installare dipendenze Poetry
# -------------------------------------------------------------
echo "📦 Installazione/aggiornamento dipendenze..."
poetry install --no-interaction --no-root

# -------------------------------------------------------------
# 4️⃣ Esecuzione facoltativa dei test
# -------------------------------------------------------------
if [[ "${RUN_TESTS:-0}" == "1" ]]; then
  echo "🧪 Esecuzione test (RUN_TESTS=1)..."
  poetry run pytest
else
  echo "⏭  Test disattivati (default). Imposta RUN_TESTS=1 per abilitarli."
fi

# -------------------------------------------------------------
# 5️⃣ Build pulita degli artifact locali
# -------------------------------------------------------------
echo "🏗️ Build pulita del pacchetto..."
poetry build --clean

echo ""
echo "✅ Verifica locale pre-rilascio completata."
echo "   - Versione: $VERSION"
echo "   - Tag git trovato: $TAG"
echo "   - Artifact creati in: $PROJECT_ROOT/dist"
echo ""
echo "🚀 Per pubblicare su PyPI:"
echo "   1. Configura su PyPI il pending Trusted Publisher per '$PACKAGE_NAME'."
echo "   2. Crea una GitHub Release pubblicata sul tag '$TAG'."
echo "   3. Il workflow '.github/workflows/release.yml' pubblicherà gli artifact su PyPI."
echo ""
