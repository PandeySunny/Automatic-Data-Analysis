# Data Analysis Automation Project

A Flask-based web application for automated CSV data analysis and visualization.

## Quick Start

1. Create and activate virtual environment (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
```

3. Run the application:
```powershell
python app.py
```

4. Open http://127.0.0.1:5000/ in your browser

## Features

- Upload CSV files (up to 500MB)
- Automatic data cleaning (removes nulls and duplicates)
- Dataset summary statistics
- Automated visualizations:
  - Histograms for numeric columns
  - Boxplots for distributions
  - Pie charts for categorical data
  - Bar charts for top categories
  - Correlation heatmap for numeric columns
- Large file handling with automatic sampling
- Clean, responsive UI

## Project Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── static/
│   ├── style.css         # UI styling
│   └── plots/            # Generated visualizations
├── templates/
│   ├── upload.html       # File upload page
│   └── results.html      # Analysis results page
└── uploads/              # Stored CSV files
```

## Dependencies

- Flask==2.3.2
- Werkzeug==2.3.6
- pandas==2.1.0
- matplotlib==3.8.0
- seaborn==0.13.0

## Usage Flow

1. Visit the upload page
2. Select a CSV file and click "Submit (Upload)"
3. Click "Analyze" to process the file
4. View generated summary statistics and visualizations

## Notes

- Uploads are stored in `uploads/` with unique timestamped filenames
- Visualizations are saved as PNGs in `static/plots/`
- Large files (>100k rows) are analyzed using a sample
- Debug mode is enabled by default (disable for production)