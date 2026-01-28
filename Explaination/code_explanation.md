# Code Explanation: Data Analysis Automation Project

## 1. Imports and Setup
```python
import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
```
- Imports required libraries for:
  - File handling (os, uuid)
  - Web framework (Flask)
  - Data processing (pandas)
  - Visualization (matplotlib, seaborn)

## 2. Configuration
```python
UPLOAD_FOLDER = "uploads"
PLOTS_FOLDER = "static/plots"
ALLOWED_EXTENSIONS = {"csv"}
SECRET_KEY = "change-this-to-a-random-secret-key"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PLOTS_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PLOTS_FOLDER"] = PLOTS_FOLDER
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB limit
```
- Sets up folders for uploads and plots
- Configures Flask app settings
- Sets 500MB file size limit

## 3. Helper Functions

### File Validation
```python
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
```
- Checks if uploaded file has .csv extension

### Unique Filename Generation
```python
def unique_path(folder, name):
    base, ext = os.path.splitext(name)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    uniq = f"{base}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
    return os.path.join(folder, uniq)
```
- Creates unique filenames using:
  - Original filename
  - Timestamp
  - Random UUID fragment
- Prevents file overwriting

### Plot Generation
```python
def generate_plots(df, prefix):
    """Generates plots (from df) and returns list of web paths like '/static/plots/xxx.png'."""
```
Creates multiple types of visualizations:
1. Histograms (up to 6 numeric columns)
   - Shows distribution of numeric data
   - Includes KDE (Kernel Density Estimation)

2. Boxplots (up to 3 numeric columns)
   - Shows median, quartiles, and outliers
   - Good for identifying data spread

3. Pie Charts (up to 3 categorical columns)
   - Shows category distributions
   - Limited to top 6 categories

4. Bar Charts (first categorical column)
   - Shows top 10 categories
   - Good for frequency analysis

5. Correlation Heatmap
   - Shows relationships between numeric columns
   - Only generated if 2+ numeric columns exist

### Data Summary
```python
def dataset_summary(df):
    """Return a DataFrame summarizing columns (dtype, non-null count, unique, mean/std if numeric)."""
```
Creates a summary table with:
- Column names
- Data types
- Non-null counts
- Unique value counts
- Sample values
- Mean/std for numeric columns

## 4. Main Routes

### Upload Route (/)
```python
@app.route("/", methods=["GET", "POST"])
def upload_file():
```
Handles:
1. GET: Shows upload form
2. POST with action="upload":
   - Validates file
   - Saves to unique path
   - Stores filename in session
3. POST with action="analyze":
   - Redirects to results page

### Results Route (/results)
```python
@app.route("/results")
def results():
```
Processing flow:
1. Gets filename from session
2. Attempts to read full CSV
3. Falls back to 100k sample if needed
4. Cleans data (removes nulls/duplicates)
5. Generates:
   - Dataset summary
   - Sample rows preview
   - Visualizations
6. Renders results template

## 5. Error Handling

### Large File Handler
```python
@app.errorhandler(413)
def too_large(e):
    return "File is too large! Please upload a file smaller than 500 MB.", 413
```
- Returns friendly message for oversized files

### Other Error Handling
- Checks for missing files
- Validates file extensions
- Handles memory errors with sampling
- Catches plot generation errors

## 6. Data Flow Example

1. User uploads "data.csv" (200k rows):
   ```
   POST / (action="upload")
   → saves as "data_20251103120000_abc123.csv"
   → stores filename in session
   ```

2. User clicks "Analyze":
   ```
   POST / (action="analyze")
   → redirects to /results
   ```

3. Results processing:
   ```python
   # Try full load
   df = pd.read_csv(path)
   
   # If memory error, sample
   df = next(pd.read_csv(path, chunksize=100000))
   
   # Clean data
   df = df.dropna().drop_duplicates()
   
   # Generate artifacts
   summary = dataset_summary(df)
   plots = generate_plots(df, prefix)
   ```

4. Display results:
   ```
   render_template("results.html",
                  summary=summary,
                  plots=plots,
                  ...)
   ```

## 7. Key Features

### Large File Handling
- Attempts full file read first
- Falls back to 100k row sample
- Uses chunked reading for efficiency

### Data Cleaning
- Removes null values
- Removes duplicate rows
- Preserves original file

### Visualization
- Automatic plot type selection
- Handles missing data
- Limits plot counts for performance
- Saves as static PNG files

### Security
- Validates file extensions
- Limits file size
- Uses secure filenames
- Stores files with unique names

## 8. Performance Considerations

- Uses matplotlib's "Agg" backend (non-interactive)
- Samples large datasets
- Limits number of plots generated
- Uses threaded Flask server