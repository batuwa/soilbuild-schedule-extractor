#!/bin/bash

# Door Schedule Extractor - Run Script
echo "🚪 Starting Door Schedule Extractor & Viewer..."
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null
then
    echo "❌ Streamlit is not installed."
    echo "Installing requirements..."
    pip install -r requirements.txt
    echo ""
fi

# Check if PDF files exist
if [ ! -f "Kallang_Door_Schedule.pdf" ] && [ ! -f "Bedok Kembangan_door schedule.pdf" ]; then
    echo "⚠️  Warning: No PDF files found in the current directory"
    echo "Please ensure at least one of these files exists:"
    echo "  - Kallang_Door_Schedule.pdf"
    echo "  - Bedok Kembangan_door schedule.pdf"
    echo ""
fi

# Run the Streamlit app
echo "🚀 Launching Streamlit app..."
echo "The app will open in your default browser at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run app.py
