import os
import logging
import subprocess
from datetime import datetime
import sys
import pytesseract

# --- 1. SETUP LOGGING ---
# A log file is created to record the progress and any errors that occur during the pipeline run.
log_filename = "pipeline.log"
try:
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.info("Starting the full pipeline execution...")
except Exception as e:
    # Fallback to print if logging setup fails
    print(f"ERROR: Could not set up logging to {log_filename}. Check file permissions. Error: {e}")
    sys.exit(1)

# --- 2. DEFINE DIRECTORIES ---
dataset_dir = "Data Sets"
out_dir = "Out_put"
ready_dir = "Ready_dataset"
transformed_ready_dir = "Ready_Dataset_Transformed_Output"
model_ready_dir = "Model_Ready_Dataset"
split_dir = "Split_Dataset"

script_dir = os.path.dirname(os.path.abspath(__file__))

os.makedirs(ready_dir, exist_ok=True)
os.makedirs(out_dir, exist_ok=True)
os.makedirs(split_dir, exist_ok=True)
os.makedirs(model_ready_dir, exist_ok=True)
os.makedirs(transformed_ready_dir, exist_ok=True)
os.makedirs(dataset_dir, exist_ok=True)

# Note on Tesseract OCR:
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# --- 3. PIPELINE STAGES ---

# Stage 1: Match Question Papers and Marking Schemes
logging.info("Stage 1: Running QA_Match_Picker.py to find matching PDF pairs.")
print("Running Stage 1...") # Added print for immediate feedback
try:
    match_picker_script_path = os.path.join(script_dir, "QA_Match_Picker.py")
    subprocess.run(["python3", match_picker_script_path, dataset_dir, out_dir], check=True)
    logging.info("Stage 1: Completed successfully. Matched pairs are in the 'Out_put' directory.")
except subprocess.CalledProcessError as e:
    logging.error(f"Stage 1 failed: {e}")
    sys.exit(1)

# Stage 2: Process and Merge Each Matched Pair
logging.info("Stage 2: Processing and merging each matched pair...")
print("Running Stage 2...") # Added print for immediate feedback
matched_pairs_dirs = [d for d in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, d))]

if not matched_pairs_dirs:
    logging.warning("No matched directories found in 'Out_put'. Exiting pipeline.")
    sys.exit(0)

for match_dir in matched_pairs_dirs:
    match_path = os.path.join(out_dir, match_dir)
    pdf_files = [f for f in os.listdir(match_path) if f.endswith('.pdf')]
    qp_file = next((f for f in pdf_files if 'QP' in f or 'qp' in f), None)
    ms_file = next((f for f in pdf_files if 'MS' in f or 'ms' in f), None)

    if not qp_file or not ms_file:
        logging.warning(f"Skipping directory '{match_dir}': Missing either QP or MS PDF.")
        continue

    # Process Question Paper
    logging.info(f"Processing question paper: {qp_file}")
    qp_json_path = os.path.join(match_path, "extracted_questions.json")
    try:
        qp_script_path = os.path.join(script_dir, "extracted_questions_to_text.py")
        subprocess.run(["python3", qp_script_path, os.path.join(match_path, qp_file), os.path.join(match_path, "qp_diagrams"), qp_json_path], check=True)
        logging.info("Question paper processed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to process question paper '{qp_file}': {e}")
        continue

    # Process Marking Scheme
    logging.info(f"Processing marking scheme: {ms_file}")
    ms_json_path = os.path.join(match_path, "extracted_marking_scheme.json")
    try:
        ms_script_path = os.path.join(script_dir, "marking_scheme_to_text_js.py")
        subprocess.run(["python3", ms_script_path, os.path.join(match_path, ms_file), os.path.join(match_path, "ms_diagrams"), ms_json_path], check=True)
        logging.info("Marking scheme processed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to process marking scheme '{ms_file}': {e}")
        continue

    # Merge QA Pairs
    logging.info(f"Merging data for {match_dir}")
    try:
        merge_script_path = os.path.join(script_dir, "merged_question_marking_scheme_js.py")
        subprocess.run(["python3", merge_script_path, qp_json_path, ms_json_path, ready_dir], check=True)
        logging.info("Merging completed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to merge data for '{match_dir}': {e}")
        continue

logging.info("Stage 2: All matched pairs processed.")

# Stage 3: Transform JSON Files
logging.info("Stage 3: Running json_file_transformer_updated.py to restructure JSON data.")
print("Running Stage 3...") # Added print for immediate feedback
try:
    transform_script_path = os.path.join(script_dir, "json_file_transformer_updated.py")
    subprocess.run(["python3", transform_script_path, ready_dir, transformed_ready_dir], check=True)
    logging.info("Stage 3: Transformation completed successfully.")
except subprocess.CalledProcessError as e:
    logging.error(f"Stage 3 failed: {e}")
    sys.exit(1)

# Stage 4: Prepare Model-Ready Dataset
logging.info("Stage 4: Running prepare_model_ready_dataset_enhanced.py to prepare data for a model.")
print("Running Stage 4...") # Added print for immediate feedback
try:
    prepare_script_path = os.path.join(script_dir, "prepare_model_ready_dataset_enhanced.py")
    subprocess.run(["python3", prepare_script_path, transformed_ready_dir, model_ready_dir], check=True)
    logging.info("Stage 4: Dataset prepared successfully.")
except subprocess.CalledProcessError as e:
    logging.error(f"Stage 4 failed: {e}")
    sys.exit(1)

# Stage 5: Split the Dataset
logging.info("Stage 5: Running split_clean.py to split the dataset.")
print("Running Stage 5...") # Added print for immediate feedback
try:
    split_script_path = os.path.join(script_dir, "split_clean.py")
    subprocess.run(["python3", split_script_path, model_ready_dir, split_dir], check=True)
    logging.info("Stage 5: Dataset split into train/test/validation sets successfully.")
except subprocess.CalledProcessError as e:
    logging.error(f"Stage 5 failed: {e}")
    sys.exit(1)

logging.info("Full pipeline execution completed successfully.")
print("\n✓ The full pipeline has finished. Check 'pipeline.log' for details.")
print("✓ Final datasets are located in the 'Split_Dataset' directory.")