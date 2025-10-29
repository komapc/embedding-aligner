#!/bin/bash
# Download Wikipedia dumps for Ido and Esperanto

set -e

DATA_DIR="data/raw"
mkdir -p "$DATA_DIR"

echo "Downloading Ido Wikipedia dump..."
wget -c https://dumps.wikimedia.org/iowiki/latest/iowiki-latest-pages-articles.xml.bz2 \
    -O "$DATA_DIR/iowiki-latest-pages-articles.xml.bz2"

echo "Downloading Esperanto Wikipedia dump..."
wget -c https://dumps.wikimedia.org/eowiki/latest/eowiki-latest-pages-articles.xml.bz2 \
    -O "$DATA_DIR/eowiki-latest-pages-articles.xml.bz2"

echo "Download complete!"
echo "Ido dump: $DATA_DIR/iowiki-latest-pages-articles.xml.bz2"
echo "Esperanto dump: $DATA_DIR/eowiki-latest-pages-articles.xml.bz2"
