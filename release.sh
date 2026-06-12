#!/usr/bin/env bash
#
# Script di rilascio per il progetto istat-census-data:
# - build + pubblicazione del pacchetto su PyPI usando Poetry
# - deploy documentazione su GitHub Pages tramite MkDocs
#
# Uso:
#   ./release.sh
#   RUN_TESTS=1 ./release.sh   # per eseguire i test
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
VERSION=$(python3 - << 'EOF'
import tomllib, pathlib
data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
print(data["tool"]["poetry"]["version"])
EOF
)

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
# 3️⃣ Chiedere/configurare il token PyPI
# -------------------------------------------------------------
if [[ -z "${POETRY_PYPI_TOKEN_PYPI:-}" ]]; then
    echo ""
    echo "🔐 Nessun token PyPI trovato."
    echo "Inserisci il token PyPI (inizia per 'pypi-'):"
    read -rsp "Token: " TOKEN
    echo ""

    if [[ -z "$TOKEN" ]]; then
        echo "❌ Nessun token inserito. Pubblicazione annullata."
        exit 1
    fi

    export POETRY_PYPI_TOKEN_PYPI="$TOKEN"
    echo "🔑 Token salvato per questa sessione."
else
    echo "🔑 Token PyPI rilevato dalla variabile d'ambiente."
    TOKEN="$POETRY_PYPI_TOKEN_PYPI"
fi

echo "⚙️ Configuro il token anche nella config di Poetry (pypi-token.pypi)..."
poetry config pypi-token.pypi "$TOKEN" --local || poetry config pypi-token.pypi "$TOKEN"

echo "🔎 Configurazione Poetry relativa a PyPI:"
poetry config --list | grep -i "pypi" || echo "Nessuna voce pypi-* trovata in poetry config."

# -------------------------------------------------------------
# 4️⃣ Installare dipendenze Poetry
# -------------------------------------------------------------
echo "📦 Installazione/aggiornamento dipendenze..."
poetry install --no-interaction --no-root

# -------------------------------------------------------------
# 5️⃣ Esecuzione facoltativa dei test
# -------------------------------------------------------------
if [[ "${RUN_TESTS:-0}" == "1" ]]; then
  echo "🧪 Esecuzione test (RUN_TESTS=1)..."
  poetry run pytest
else
  echo "⏭  Test disattivati (default). Imposta RUN_TESTS=1 per abilitarli."
fi

# -------------------------------------------------------------
# 6️⃣ Build + publish su PyPI (verbose)
# -------------------------------------------------------------
echo "🚀 Build e pubblicazione su PyPI (poetry publish -vvv)..."
set -x  # traccia i comandi per vedere meglio cosa succede
poetry publish --build -vvv
set +x

# -------------------------------------------------------------
# 7️⃣ Deploy documentazione MkDocs
# -------------------------------------------------------------
echo "📚 Deploy documentazione su GitHub Pages..."
poetry run mkdocs gh-deploy --clean

echo ""
echo "🎉 Rilascio completato con successo!"
echo "   - Versione: $VERSION"
echo "   - Tag git trovato: $TAG"
echo "   - Pubblicato su PyPI"
echo "   - Documentazione aggiornata su GitHub Pages"
echo ""
