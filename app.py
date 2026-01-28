import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import traceback
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import numpy as np

# --- Configuration ---
UPLOAD_FOLDER = "uploads"
PLOTS_FOLDER = "static/plots"
ALLOWED_EXTENSIONS = {"csv"}
SECRET_KEY = "change-this-to-a-random-secret-key"  # change before deployment

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PLOTS_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PLOTS_FOLDER"] = PLOTS_FOLDER
app.secret_key = SECRET_KEY

# Allow uploads up to 500 MB
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

sns.set(style="whitegrid")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def unique_path(folder, name):
    base, ext = os.path.splitext(name)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    uniq = f"{base}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
    return os.path.join(folder, uniq)


def convert_datetime_columns(df):
    """Convert datetime columns to year, month, day columns."""
    df_copy = df.copy()
    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            try:
                df_copy[f"{col}_year"] = df_copy[col].dt.year
                df_copy[f"{col}_month"] = df_copy[col].dt.month
                df_copy[f"{col}_day"] = df_copy[col].dt.day
                df_copy = df_copy.drop(columns=[col])
                app.logger.info(f"Converted datetime column '{col}' to year/month/day")
            except Exception as e:
                app.logger.warning(f"Failed to convert datetime column '{col}': {e}")
    return df_copy


def detect_financial_columns(df):
    """Heuristic to identify likely financial columns."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    financial_keywords = ["amount", "balance", "price", "cost", "revenue", "expense", "profit", "salary", "income", "transaction"]
    
    likely_financial = []
    for col in numeric_cols:
        if any(keyword in col.lower() for keyword in financial_keywords):
            likely_financial.append(col)
    
    # If no explicit matches, just use all numeric columns if they exist
    return likely_financial if likely_financial else numeric_cols


def perform_fintech_analysis(df):
    """
    Performs K-Means Clustering for segmentation and Isolation Forest for fraud/anomaly detection.
    Returns a dictionary with results.
    """
    results = {
        "segments": None,
        "anomalies": None,
        "pca_data": None,
        "segment_profiles": None,
        "fraud_count": 0
    }
    
    # 1. Select Features
    features = detect_financial_columns(df)
    if len(features) < 1:
        return results

    X = df[features].copy()
    
    # 2. Preprocessing (Impute & Scale)
    try:
        imputer = SimpleImputer(strategy="mean")
        X_imputed = imputer.fit_transform(X)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_imputed)
    except Exception as e:
        app.logger.error(f"Preprocessing failed: {e}")
        return results

    # 3. Clustering (Segmentation) - Default to 3 segments (faster than 4)
    try:
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=5)  # Reduced from n_init=10 to 5
        clusters = kmeans.fit_predict(X_scaled)
        df["Segment"] = clusters
        results["segments"] = clusters
        
        # Calculate Segment Profiles (Mean values of features)
        profiles = df.groupby("Segment")[features].mean().reset_index()
        results["segment_profiles"] = profiles.to_dict(orient="records")
    except Exception as e:
        app.logger.error(f"Clustering failed: {e}")

    # 4. Anomaly Detection (Fraud Risk) - Contamination 1%
    try:
        iso = IsolationForest(contamination=0.01, random_state=42)
        anomalies = iso.fit_predict(X_scaled)
        # IsolationForest returns -1 for anomalies, 1 for normal. Map to Boolean or Label.
        df["Is_Anomaly"] = anomalies == -1
        results["anomalies"] = df["Is_Anomaly"].values
        results["fraud_count"] = int(df["Is_Anomaly"].sum())
    except Exception as e:
        app.logger.error(f"Anomaly Detection failed: {e}")

    # 5. PCA for Visualization (2D)
    try:
        if X_scaled.shape[1] >= 2:
            pca = PCA(n_components=2)
            coords = pca.fit_transform(X_scaled)
            results["pca_data"] = coords
    except Exception as e:
        app.logger.error(f"PCA failed: {e}")

    return results


def generate_plots(df, prefix, ml_results=None):
    """Generates plots (from df) and returns list of web paths like '/static/plots/xxx.png'."""
    plot_files = []
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    # Histograms (up to 3) - Reduced from 6 for speed
    for col in numeric[:3]:
        try:
            plt.figure(figsize=(6, 4))
            sns.histplot(df[col].dropna(), kde=True, bins=30)
            plt.title(f"Histogram: {col}")
            fname = f"{prefix}_hist_{col}.png".replace(" ", "_")
            path = os.path.join(app.config["PLOTS_FOLDER"], fname)
            plt.tight_layout()
            plt.savefig(path, dpi=80)  # Reduced DPI for speed
            plt.close()
            plot_files.append(f"/static/plots/{fname}")
        except Exception:
            app.logger.exception("Failed to create histogram for %s", col)

    # Boxplots (up to 2) - Reduced from 3
    for col in numeric[:2]:
        try:
            plt.figure(figsize=(6, 3))
            sns.boxplot(x=df[col].dropna())
            plt.title(f"Boxplot: {col}")
            fname = f"{prefix}_box_{col}.png".replace(" ", "_")
            path = os.path.join(app.config["PLOTS_FOLDER"], fname)
            plt.tight_layout()
            plt.savefig(path, dpi=80)
            plt.close()
            plot_files.append(f"/static/plots/{fname}")
        except Exception:
            app.logger.exception("Failed to create boxplot for %s", col)

    # Pie charts for categorical top counts (up to 2) - Reduced from 3
    for col in categorical[:2]:
        try:
            counts = df[col].fillna("<<Missing>>").value_counts().nlargest(6)
            if counts.sum() == 0:
                continue
            plt.figure(figsize=(5, 5))
            counts.plot.pie(autopct="%1.1f%%", startangle=90)
            plt.ylabel("")
            plt.title(f"Distribution: {col}")
            fname = f"{prefix}_pie_{col}.png".replace(" ", "_")
            path = os.path.join(app.config["PLOTS_FOLDER"], fname)
            plt.tight_layout()
            plt.savefig(path, dpi=80)
            plt.close()
            plot_files.append(f"/static/plots/{fname}")
        except Exception:
            app.logger.exception("Failed to create pie chart for %s", col)

    # Bar chart for top categories (first categorical)
    if categorical:
        col = categorical[0]
        try:
            counts = df[col].fillna("<<Missing>>").value_counts().nlargest(10)
            plt.figure(figsize=(8, 4))
            sns.barplot(x=counts.values, y=counts.index)
            plt.title(f"Top categories: {col}")
            fname = f"{prefix}_bar_{col}.png".replace(" ", "_")
            path = os.path.join(app.config["PLOTS_FOLDER"], fname)
            plt.tight_layout()
            plt.savefig(path, dpi=80)
            plt.close()
            plot_files.append(f"/static/plots/{fname}")
        except Exception:
            app.logger.exception("Failed to create bar chart for %s", col)

    # Correlation heatmap for numeric features (if >=2)
    if len(numeric) >= 2:
        try:
            corr = df[numeric].corr()
            plt.figure(figsize=(8, 6))
            sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1)
            plt.title("Correlation heatmap")
            fname = f"{prefix}_corr.png".replace(" ", "_")
            path = os.path.join(app.config["PLOTS_FOLDER"], fname)
            plt.tight_layout()
            plt.savefig(path, dpi=80)
            plt.close()
            plot_files.append(f"/static/plots/{fname}")
        except Exception:
            app.logger.exception("Failed to create correlation heatmap")

    # --- Fintech ML Plots ---
    if ml_results and ml_results.get("pca_data") is not None:
        pca_data = ml_results["pca_data"]
        
        # 1. Segmentation Plot
        try:
            plt.figure(figsize=(8, 6))
            segments = ml_results.get("segments")
            if segments is not None:
                sns.scatterplot(x=pca_data[:, 0], y=pca_data[:, 1], hue=segments, palette="viridis", s=60)
                plt.title("Customer Segmentation (PCA projection)")
                plt.xlabel("Principal Component 1")
                plt.ylabel("Principal Component 2")
                fname = f"{prefix}_segmentation.png".replace(" ", "_")
                path = os.path.join(app.config["PLOTS_FOLDER"], fname)
                plt.tight_layout()
                plt.savefig(path, dpi=80)
                plt.close()
                plot_files.append(f"/static/plots/{fname}")
        except Exception:
            app.logger.exception("Failed to create segmentation plot")

        # 2. Fraud/Anomaly Plot
        try:
            plt.figure(figsize=(8, 6))
            anomalies = ml_results.get("anomalies")
            if anomalies is not None:
                # Color code: Blue (Normal), Red (High Risk)
                colors = ["red" if x else "blue" for x in anomalies]
                plt.scatter(pca_data[:, 0], pca_data[:, 1], c=colors, s=60, alpha=0.6)
                # Create a custom legend
                from matplotlib.lines import Line2D
                legend_elements = [Line2D([0], [0], marker='o', color='w', label='Normal', markerfacecolor='blue', markersize=10),
                                   Line2D([0], [0], marker='o', color='w', label='Potential Fraud', markerfacecolor='red', markersize=10)]
                plt.legend(handles=legend_elements)
                
                plt.title("Fraud Risk Visualizer (PCA projection)")
                plt.xlabel("Principal Component 1")
                plt.ylabel("Principal Component 2")
                fname = f"{prefix}_fraud.png".replace(" ", "_")
                path = os.path.join(app.config["PLOTS_FOLDER"], fname)
                plt.tight_layout()
                plt.savefig(path, dpi=80)
                plt.close()
                plot_files.append(f"/static/plots/{fname}")
        except Exception:
            app.logger.exception("Failed to create fraud plot")

    return plot_files


def dataset_summary(df):
    """Return a DataFrame summarizing columns (dtype, non-null count, unique, mean/std if numeric)."""
    rows = []
    for col in df.columns:
        try:
            dtype = str(df[col].dtype)
            non_null = int(df[col].notna().sum())
            unique = int(df[col].nunique(dropna=True))
            sample = str(df[col].dropna().iloc[0]) if non_null > 0 else ""
            info = {"column": col, "dtype": dtype, "non_null_count": non_null, "unique_values": unique, "sample_value": sample}
            if pd.api.types.is_numeric_dtype(df[col]):
                info["mean"] = float(df[col].mean(skipna=True)) if non_null else None
                info["std"] = float(df[col].std(skipna=True)) if non_null else None
            else:
                info["mean"] = None
                info["std"] = None
            rows.append(info)
        except Exception:
            app.logger.exception("Error summarizing column %s", col)
    return pd.DataFrame(rows)


def generate_dataset_explanation(df, filename, summary_source="full file"):
    """Generate a comprehensive explanation of the dataset."""
    total_rows, total_cols = df.shape
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    
    # Calculate data quality metrics
    total_cells = total_rows * total_cols
    missing_cells = df.isna().sum().sum()
    completeness = ((total_cells - missing_cells) / total_cells * 100) if total_cells > 0 else 0
    
    duplicate_rows = df.duplicated().sum()
    
    # Memory usage
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    
    explanation = {
        "filename": filename,
        "total_rows": total_rows,
        "total_cols": total_cols,
        "numeric_cols": len(numeric_cols),
        "categorical_cols": len(categorical_cols),
        "completeness_percent": round(completeness, 2),
        "duplicate_rows": duplicate_rows,
        "memory_mb": round(memory_mb, 2),
        "summary_source": summary_source,
        "column_list": list(df.columns),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "quality_status": "✅ High Quality" if completeness > 95 and duplicate_rows == 0 else "⚠️ Needs Attention"
    }
    
    return explanation


def generate_chart_explanations():
    """Generate simple explanations for basic chart types."""
    explanations = {
        "hist": {
            "title": "📊 Distribution",
            "description": "Shows how values are spread across ranges."
        },
        "box": {
            "title": "📦 Outliers",
            "description": "Displays data spread and highlights unusual values."
        },
        "pie": {
            "title": "🥧 Proportions",
            "description": "Shows percentage breakdown of categories."
        },
        "bar": {
            "title": "📊 Comparison",
            "description": "Compares frequencies across categories."
        },
        "corr": {
            "title": "🔥 Relationships",
            "description": "Shows how variables relate to each other."
        }
    }
    return explanations


def generate_dataset_explanation(df, filename, summary_source):
    """Generate comprehensive dataset explanation for the template."""
    import sys
    
    # Calculate duplicate rows (before cleaning)
    # Since we already cleaned the data, we'll use 0 for now or could track it earlier
    duplicate_rows = 0
    
    # Get numeric and categorical columns
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    
    # Calculate data completeness
    total_cells = df.shape[0] * df.shape[1]
    non_null_cells = df.notna().sum().sum()
    completeness_percent = round((non_null_cells / total_cells * 100) if total_cells > 0 else 0, 1)
    
    # Determine quality status
    if completeness_percent >= 95:
        quality_status = "Excellent"
    elif completeness_percent >= 80:
        quality_status = "Good"
    elif completeness_percent >= 60:
        quality_status = "Fair"
    else:
        quality_status = "Poor"
    
    # Calculate memory usage in MB
    memory_bytes = df.memory_usage(deep=True).sum()
    memory_mb = round(memory_bytes / (1024 * 1024), 2)
    
    explanation = {
        "total_rows": df.shape[0],
        "total_cols": df.shape[1],
        "completeness_percent": completeness_percent,
        "quality_status": quality_status,
        "filename": filename,
        "summary_source": summary_source,
        "memory_mb": memory_mb,
        "numeric_cols": len(numeric_cols),
        "categorical_cols": len(categorical_cols),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "duplicate_rows": duplicate_rows
    }
    
    return explanation


# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def upload_file():
    message = None
    uploaded_filename = session.get("uploaded_filename", None)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "upload":
            if "file" not in request.files:
                flash("No file part")
                return redirect(request.url)
            file = request.files["file"]
            if file.filename == "":
                flash("No selected file")
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                path = unique_path(app.config["UPLOAD_FOLDER"], filename)
                file.save(path)
                basename = os.path.basename(path)
                session["uploaded_filename"] = basename  # store only basename
                size_mb = os.path.getsize(path) / (1024 * 1024)
                message = f"Uploaded {basename} ({size_mb:.2f} MB)"
                app.logger.info("Saved upload to %s (%.2f MB)", path, size_mb)
            else:
                flash("Allowed file types: csv")
                return redirect(request.url)
        elif action == "analyze":
            if not uploaded_filename:
                flash("No file uploaded yet. Please upload a CSV first.")
                return redirect(request.url)
            return redirect(url_for("results"))
    return render_template("upload.html", message=message, uploaded_filename=uploaded_filename)


@app.route("/results")
def results():
    uploaded_basename = session.get("uploaded_filename", None)
    if not uploaded_basename:
        flash("No file available for analysis. Please upload a CSV first.")
        return redirect(url_for("upload_file"))

    full_path = os.path.join(app.config["UPLOAD_FOLDER"], uploaded_basename)
    if not os.path.exists(full_path):
        flash("Uploaded file missing on server. Please re-upload.")
        session.pop("uploaded_filename", None)
        return redirect(url_for("upload_file"))

    file_size_mb = os.path.getsize(full_path) / (1024 * 1024)
    app.logger.info("Preparing analysis for %s (%.2f MB)", full_path, file_size_mb)

    # Try reading the full file, fallback to sample if memory fails or other errors
    df = None
    loaded_full = False
    try:
        df = pd.read_csv(full_path, low_memory=False, parse_dates=True)
        loaded_full = True
        app.logger.info("Loaded full CSV with shape %s", df.shape)
    except MemoryError:
        app.logger.exception("MemoryError while reading full CSV - will try sample")
    except Exception as e:
        app.logger.warning("Could not read full CSV (%s). Will attempt to read sample. Trace: %s", e, traceback.format_exc())

    if not loaded_full:
        try:
            chunks = pd.read_csv(full_path, chunksize=100000, parse_dates=True)
            df_sample = next(chunks)
            df = df_sample
            flash("Full file could not be loaded into memory. Analysis performed on a 100k-row sample.")
            app.logger.info("Loaded sample from CSV with shape %s", df.shape)
        except Exception as e:
            app.logger.exception("Failed to read sample from CSV: %s", e)
            flash(f"Failed to read file for analysis: {e}")
            return redirect(url_for("upload_file"))
    
    # --- Convert datetime columns to year/month/day ---
    df = convert_datetime_columns(df)

    # --- CLEANING STEP: remove nulls and duplicates ---
    before_shape = df.shape
    df = df.dropna().drop_duplicates()
    after_shape = df.shape
    app.logger.info("Cleaned dataset: from %s to %s (removed nulls & duplicates)", before_shape, after_shape)

    # Use df for summary
    summary_source = "full file" if loaded_full else "sample"
    summary_df = dataset_summary(df)

    # Rows / cols
    rows, cols = df.shape

    # Prepare sample_for_plots: if dataset too big, sample up to 100k rows
    try:
        if len(df) > 100000:
            sample_for_plots = df.sample(n=100000, random_state=42)
        else:
            sample_for_plots = df
    except Exception:
        sample_for_plots = df.head(100000)

    # Render head (sample)
    head_html = sample_for_plots.head(10).to_html(classes="table-sample", index=False, escape=False)
    summary_html = summary_df.to_html(classes="invisible-border-table", index=False, float_format="%.3f", na_rep="")

    # Run Fintech ML Analysis
    ml_results = perform_fintech_analysis(sample_for_plots)

    # Generate plots
    prefix = os.path.splitext(uploaded_basename)[0]
    try:
        plots = generate_plots(sample_for_plots, prefix, ml_results=ml_results)
    except Exception:
        app.logger.exception("Failed to generate plots")
        plots = []

    # Generate explanations
    dataset_explanation = generate_dataset_explanation(df, uploaded_basename, summary_source)
    chart_explanations = generate_chart_explanations()

    return render_template("results.html",
                           filename=uploaded_basename,
                           rows=rows,
                           cols=cols,
                           head=head_html,
                           summary_html=summary_html,
                           plots=plots,
                           summary_source=summary_source,
                           ml_results=ml_results,
                           dataset_explanation=dataset_explanation,
                           chart_explanations=chart_explanations)


# Friendly error message for oversized payloads
@app.errorhandler(413)
def too_large(e):
    return "File is too large! Please upload a file smaller than 500 MB.", 413


if __name__ == "__main__":
    app.run(debug=False, threaded=True)  # debug=False for faster performance