#!/bin/bash

# Update package list
apt-get update

# Install system dependencies
xargs apt-get install -y < packages.txt

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt

# Verify WeasyPrint installation
python -c "import weasyprint; print('WeasyPrint version:', weasyprint.__version__)"