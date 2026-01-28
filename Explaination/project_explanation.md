# Project Technical Documentation

## Architecture and Data Flow

### Components
- Flask web application (app.py)
- File upload handler with size/type validation
- Pandas-based data processing
- Matplotlib/Seaborn visualization generation
- Session-based user state management
- Static file serving (plots and styles)

### Data Flow
1. User uploads CSV via web form
2. Server validates and saves file with unique name
3. Analysis process:
   - Attempts full file read
   - Falls back to 100k sample if needed
   - Cleans data (null/duplicate removal)
   - Generates summary statistics
   - Creates visualizations
4. Results displayed in web interface

## Code Walkthrough

### Key Functions

#### File Handling
```python
def allowed_file(filename):
    # Validates .csv extension
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def unique_path(folder, name):
    # Creates timestamped unique filename
    base, ext = os.path.splitext(name)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    uniq = f"{base}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
    return os.path.join(folder, uniq)
```

#### Data Processing
```python
def dataset_summary(df):
    # Generates column-level metadata
    # Returns dtype, counts, uniqueness, samples, stats
```

#### Visualization
```python
def generate_plots(df, prefix):
    # Creates various plot types:
    # - Histograms (numeric)
    # - Boxplots (distributions)
    # - Pie charts (categories)
    # - Bar charts (top values)
    # - Correlation heatmap
```

## Routes

### Upload (`/`)
- GET: Display upload form
- POST: 
  - action="upload": Save file
  - action="analyze": Redirect to results

### Results (`/results`)
- Loads and processes CSV
- Generates visualizations
- Displays summary and plots

## Interview Questions & Answers

### Implementation Choices

Q: How does the app handle large files?
A: Implements a fallback sampling strategy (100k rows) if full load fails.

Q: How are filenames kept unique?
A: Combines timestamp and UUID fragment with original name.

Q: Security considerations?
A: File extension validation, size limits, safe HTML rendering.

### Scaling & Improvements

Q: How would you scale for production?
A: 
- Move to async processing (Celery/RQ)
- Implement proper user authentication
- Add file content validation
- Use environment variables for configuration
- Add comprehensive testing
- Deploy with production WSGI server

### Technical Deep Dives

Q: Visualization strategy?
A: 
- Automatic plot type selection based on data types
- Memory-conscious sampling for large datasets
- Error handling for edge cases (few columns, missing data)

Q: Data cleaning approach?
A:
- Removes null values and duplicates
- Provides summary statistics
- Maintains original data file

## Edge Cases & Error Handling

- Oversized files (>500MB)
- Non-CSV uploads
- Memory constraints
- Missing files
- Invalid data formats
- Plot generation failures

## Testing Strategy

### Unit Tests
- File validation
- Path generation
- Data summarization
- Plot generation

### Integration Tests
- File upload flow
- Analysis process
- Error handling
- Route behavior

## Production Deployment Notes

### Security
- Set secure SECRET_KEY
- Implement user authentication
- Add file scanning
- Validate file contents
- Set up proper CORS

### Performance
- Use async processing
- Implement caching
- Add progress tracking
- Optimize large file handling

### Monitoring
- Add logging
- Track error rates
- Monitor disk usage
- Watch memory consumption

## Demo Script

1. Start application:
```powershell
python app.py
```

2. Access web interface:
- Open http://127.0.0.1:5000/

3. Demo steps:
- Upload sample CSV
- Show validation
- Trigger analysis
- Walk through results
- Explain visualizations
- Show file artifacts

## Troubleshooting

### Common Issues
- Missing plots: Check static/plots/ permissions
- Upload fails: Verify file size < 500MB
- Pandas errors: Check CSV format/encoding
- Missing dependencies: Verify requirements.txt install

### Quick Fixes
- Clear static/plots/ for fresh start
- Restart Flask server
- Check CSV file encoding
- Verify Python environment