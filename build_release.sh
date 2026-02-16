#!/bin/bash

# Ustal katalog projektu
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DIST_DIR="$PROJECT_DIR/dist"
VERSION="v1.2"
PACKAGE_NAME="RadioScheduler_${VERSION}_Linux"
OUTPUT_DIR="$DIST_DIR/$PACKAGE_NAME"

echo "--- Budowanie pakietu wydania $VERSION ---"

# 1. Przygotuj czysty katalog
rm -rf "$DIST_DIR"
mkdir -p "$OUTPUT_DIR"

# 2. Lista plików do skopiowania
FILES_TO_COPY=(
    "radio-scheduler-gui.py"
    "radio-scheduler.py"
    "mpc_controller.py"
    "translations.py"
    "requirements.txt"
    "install.sh"
    "app_icon.png"
    "README.md"
    "README.pl.md"
    "LICENSE"
)

# 3. Kopiowanie plików
for file in "${FILES_TO_COPY[@]}"; do
    if [ -f "$PROJECT_DIR/$file" ]; then
        cp "$PROJECT_DIR/$file" "$OUTPUT_DIR/"
        echo "Skopiowano: $file"
    else
        echo "Pominięto (nie znaleziono): $file"
    fi
done

# 4. Nadanie uprawnień
chmod +x "$OUTPUT_DIR/install.sh"
chmod +x "$OUTPUT_DIR/radio-scheduler-gui.py"
chmod +x "$OUTPUT_DIR/radio-scheduler.py"

# 5. Pakowanie do ZIP
echo "Tworzenie archiwum ZIP..."
cd "$DIST_DIR" || exit
zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_NAME"

echo "---------------------------------------------------"
echo "Pakiet gotowy: $DIST_DIR/${PACKAGE_NAME}.zip"
echo "Możesz załączyć ten plik do wydania na GitHubie."
