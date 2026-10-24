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

def run_script(script_name, *args):
    """
    Runs a single stage (Python script) of the pipeline using subprocess with better error handling.
    """
    script_path = os.path.join(script_dir, script_name)
    command = ["python", script_path] + list(args)
    
    logging.info(f"Running script: {script_name} with arguments: {args}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        logging.info(f"Output: {result.stdout.strip()}")
        logging.info(f"✓ Stage {script_name} completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"ERROR: Stage {script_name} failed. Return code: {e.returncode}")
        logging.error(f"STDOUT: {e.stdout.strip()}")
        logging.error(f"STDERR: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        logging.error(f"ERROR: Python interpreter not found. Ensure 'python' is in your PATH.")
        return False

# --- 3. PIPELINE STAGES ---

# Stage 1: Match Question Papers and Marking Schemes
#logging.info("Stage 1: Running QA_Match_Picker.py to find matching PDF pairs.")
#print("Running Stage 1...")
#if not run_script("QA_Match_Picker.py", dataset_dir, out_dir):
 ##  sys.exit(1)

# Stage 2: Process and Merge Each Matched Pair
#logging.info("Stage 2: Processing and merging each matched pair...")
#print("Running Stage 2...")
#matched_pairs_dirs = [d for d in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, d))]

#if not matched_pairs_dirs:
 #   logging.warning("No matched directories found in 'Out_put'. Exiting pipeline.")
  #  sys.exit(0)

#for match_dir in matched_pairs_dirs:
 #   match_path = os.path.join(out_dir, match_dir)
  #  pdf_files = [f for f in os.listdir(match_path) if f.lower().endswith('.pdf')]
   # qp_file = next((f for f in pdf_files if 'qp' in f.lower()), None)
    #ms_file = next((f for f in pdf_files if 'ms' in f.lower()), None)

    #if not qp_file or not ms_file:
     #   logging.warning(f"Skipping directory '{match_dir}': Missing either QP or MS PDF.")
      #  continue

    # Process Question Paper
    #logging.info(f"--- Processing pair: {qp_file} & {ms_file} ---")
    #qp_json_path = os.path.join(match_path, "extracted_questions.json")
    #if not run_script("extracted_questions_to_text.py", os.path.join(match_path, qp_file), os.path.join(match_path, "qp_diagrams"), qp_json_path):
     #   logging.error(f"Skipping '{match_dir}' due to question extraction failure.")
      #  continue
    
    # Check if the extracted JSON file is empty or missing
    #if not os.path.exists(qp_json_path) or os.stat(qp_json_path).st_size == 0:
     #   logging.warning(f"Skipping '{match_dir}' as question paper seems to be unstructured (empty output).")
      #  continue

    # Process Marking Scheme
    #ms_json_path = os.path.join(match_path, "extracted_marking_scheme.json")
    #if not run_script("marking_scheme_to_text_js.py", os.path.join(match_path, ms_file), os.path.join(match_path, "ms_diagrams"), ms_json_path):
     #   logging.error(f"Skipping '{match_dir}' due to marking scheme extraction failure.")
      #  continue
    
    # Check if the extracted JSON file is empty or missing
    #if not os.path.exists(ms_json_path) or os.stat(ms_json_path).st_size == 0:
     #   logging.warning(f"Skipping '{match_dir}' as marking scheme seems to be unstructured (empty output).")
      #  continue

    # Merge QA Pairs
    #merged_json_name = f"{os.path.basename(qp_file).replace('.pdf', '')}_merged.json"
    #output_ready_json = os.path.join(ready_dir, merged_json_name)
    #if not run_script("merged_question_marking_scheme_js.py", qp_json_path, ms_json_path, output_ready_json):
     #   logging.error(f"Failed to merge data for '{match_dir}'.")
      #  continue

#logging.info("Stage 2: All matched pairs processed.")

# Stage 2: Process and Merge Each Matched Pair
logging.info("Stage 2: Processing and merging each matched pair...")
print("Running Stage 2...")
matched_pairs_dirs = [d for d in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, d))]

if not matched_pairs_dirs:
    logging.warning("No matched directories found in 'Out_put'. Exiting pipeline.")
    sys.exit(0)

for match_dir in matched_pairs_dirs:
    match_path = os.path.join(out_dir, match_dir)
    pdf_files = [f for f in os.listdir(match_path) if f.lower().endswith('.pdf')]
    qp_file = next((f for f in pdf_files if 'qp' in f.lower()), None)
    ms_file = next((f for f in pdf_files if 'ms' in f.lower()), None)

    if not qp_file or not ms_file:
        logging.warning(f"Skipping directory '{match_dir}': Missing either QP or MS PDF.")
        continue

    logging.info(f"--- Processing pair: {qp_file} & {ms_file} ---")

    # Process Question Paper
    qp_json_path = os.path.join(match_path, "extracted_questions.json")
    if not run_script("extracted_questions_to_text.py", os.path.join(match_path, qp_file), os.path.join(match_path, "qp_diagrams"), qp_json_path):
        logging.error(f"Skipping '{match_dir}' due to question extraction failure.")
        continue

    if not os.path.exists(qp_json_path) or os.stat(qp_json_path).st_size == 0:
        logging.warning(f"Skipping '{match_dir}' as question paper seems to be unstructured (empty output).")
        continue

    # Process Marking Scheme
    ms_json_path = os.path.join(match_path, "extracted_marking_scheme.json")
    if not run_script("marking_scheme_to_text_js.py", os.path.join(match_path, ms_file), os.path.join(match_path, "ms_diagrams"), ms_json_path):
        logging.error(f"Skipping '{match_dir}' due to marking scheme extraction failure.")
        continue

    if not os.path.exists(ms_json_path) or os.stat(ms_json_path).st_size == 0:
        logging.warning(f"Skipping '{match_dir}' as marking scheme seems to be unstructured (empty output).")
        continue

    # Merge QA Pairs
    merged_json_name = f"{os.path.basename(qp_file).replace('.pdf', '')}_merged.json"
    output_ready_json = os.path.join(ready_dir, merged_json_name)
    if not run_script("merged_question_marking_scheme_js.py", qp_json_path, ms_json_path, output_ready_json):
        logging.error(f"Failed to merge data for '{match_dir}'.")
        continue

logging.info("Stage 2: All matched pairs processed.")



# Stage 3: Transform JSON Files
logging.info("Stage 3: Running json_file_transformer_updated.py to restructure JSON data.")
print("Running Stage 3...")
if not run_script("json_file_transformer_updated.py", ready_dir, transformed_ready_dir):
    logging.error(f"Stage 3 failed.")
    sys.exit(1)

# Stage 4: Prepare Model-Ready Dataset
logging.info("Stage 4: Running prepare_model_ready_dataset_enhanced.py to prepare data for a model.")
print("Running Stage 4...")
if not run_script("prepare_model_ready_dataset_enhanced.py", transformed_ready_dir, model_ready_dir):
    logging.error(f"Stage 4 failed.")
    sys.exit(1)

# Stage 5: Split the Dataset
logging.info("Stage 5: Running split_clean.py to split the dataset.")
print("Running Stage 5...")
if not run_script("split_clean.py", model_ready_dir, split_dir):
    logging.error(f"Stage 5 failed.")
    sys.exit(1)

logging.info("Full pipeline execution completed successfully.")
print("\n✓ The full pipeline has finished. Check 'pipeline.log' for details.")
print("✓ Final datasets are located in the 'Split_Dataset' directory.")