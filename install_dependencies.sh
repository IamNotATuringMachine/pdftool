#!/bin/bash
# This script installs the Python dependencies required for the PDF & Image Utility.

echo "Installing dependencies from requirements.txt..."

# Check if pip is available
if ! command -v pip &> /dev/null
then
    echo "pip could not be found. Please ensure Python and pip are installed and in your PATH."
    exit 1
fi

# Install dependencies
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "Dependencies installed successfully."
else
    echo "There was an error installing dependencies. Please check the output above."
    exit 1
fi

echo "Setup complete. You can now run the application using: python pdf_tool.py" 