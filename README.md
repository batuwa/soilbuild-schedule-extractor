# 🏗️ Soilbuild Demo Door Schedule Data Extractor

A tool for extracting door schedule data from PDF files. Available as both a command-line tool and a web application.

## Features

- 📄 **PDF Extraction**: Automatically extract door schedule data from PDF files
- 🌐 **Web Interface**: Simple Streamlit app for viewing and exporting data
- 💻 **Command Line**: Extract data via terminal for automation
- 💾 **Export**: Download data as JSON or CSV files

## Installation

Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Option 1: Web Application (Streamlit)

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. The app will open in your default browser at `http://localhost:8501`

3. How to use the web app:
   - Select a PDF file from the dropdown
   - Click "🔄 Extract Data from PDF"
   - View the extracted data in the table
   - Export as JSON or CSV

### Option 2: Command Line

Extract door schedule data directly from the terminal:

```bash
# Basic usage - output will be <filename>_door_schedule.json
python extract_json.py <input_pdf>

# Specify custom output filename
python extract_json.py <input_pdf> <output_json>

# Examples
python extract_json.py Kallang_Door_Schedule.pdf
python extract_json.py "Bedok Kembangan_door schedule.pdf" output.json
python extract_json.py /path/to/door_schedule.pdf /path/to/output.json
```

Get help:
```bash
python extract_json.py --help
```

## File Structure

```
door_schedule_app/
├── app.py                                    # Streamlit web application
├── extract_json.py                           # PDF extraction engine (CLI + library)
├── requirements.txt                          # Python dependencies
├── run_app.sh                                # Quick launch script for web app
├── Kallang_Door_Schedule.pdf                # Sample PDF file 1
├── Bedok Kembangan_door schedule.pdf        # Sample PDF file 2
└── README.md                                 # This file
```

## Extracted Data Format

Each door entry contains:
- `door_type`: Door type code (e.g., "MD/1", "FDM2/4A")
- `dimensions`: Door dimensions in format "XXX(W)xXXX(H)"
- `fire_rating`: Fire rating specification
- `description`: Detailed door description
- `location`: Where the door is located
- `remarks`: Additional notes and specifications

## Technical Details

### Extraction Features
- ✅ Handles multiple table formats
- ✅ Splits multi-door cells (2-6 doors per cell)
- ✅ Distinguishes variants from dimension widths
- ✅ Reconstructs split dimensions (e.g., "1" + "000(W)x..." = "1000(W)x...")
- ✅ Removes embedded fire rating text from door codes
- ✅ Handles both "FIRE-RATING" and "FIRE RATING" labels
- ✅ Filters out metadata and invalid entries

### Included Sample PDFs
1. **Kallang_Door_Schedule.pdf** - 4 pages, 64 doors
2. **Bedok Kembangan_door schedule.pdf** - 2 pages, 31 doors

## Requirements

- Python 3.8+
- streamlit >= 1.28.0
- pandas >= 2.0.0
- pdfplumber >= 0.10.0
- openpyxl >= 3.1.0

## Command-Line Arguments

```
python extract_json.py <input_pdf> [output_json]

Arguments:
  input_pdf    : Path to the PDF file to extract (required)
  output_json  : Path to output JSON file (optional)
                 Default: <input_filename>_door_schedule.json

Options:
  -h, --help   : Show help message and exit
```

## Troubleshooting

### PDF file not found
- Ensure the PDF file path is correct
- Use absolute path or relative path from current directory

### Extraction errors
- Check if the PDF has a standard door schedule table structure
- Required columns: DOOR TYPE, FIRE RATING, DESCRIPTION, LOCATION, REMARKS
- The tool will show which pages failed to extract

### Web app issues
- Make sure Streamlit is installed: `pip install streamlit`
- Check that port 8501 is not already in use
- Use `streamlit run app.py` to start the app

## License

This tool is provided as-is for internal use.

## Support

For issues or questions, please contact the development team.