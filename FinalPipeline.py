import os
import sys
import subprocess
import shutil
import logging
from datetime import datetime

# --- 1. SETUP PIPELINE CONFIGURATION & LOGGING ---
# Define directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Note: Assuming 'Data Sets' and 'Out_put' are in the same parent directory as 'Code_Snippet'
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
RAW_DATA_DIR = os.path.join(ROOT_DIR, "Data Sets")
MATCHED_PAIRS_DIR = os.path.join(ROOT_DIR, "Matched_Pairs")
EXTRACTED_DATA_DIR = os.path.join(ROOT_DIR, "Extracted_Data")

# Ensure output directories exist
os.makedirs(MATCHED_PAIRS_DIR, exist_ok=True)
os.makedirs(EXTRACTED_DATA_DIR, exist_ok=True)

# Setup logging with both file and console handlers
log_filename = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

def run_stage(script_name, *args):
    """
    Runs a single stage (Python script) of the pipeline using subprocess.
    """
    script_path = os.path.join(SCRIPT_DIR, script_name)
    command = ["python", script_path] + list(args)
    
    logging.info(f"Running script: {script_name} with arguments: {args}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        logging.info(result.stdout)
        logging.info(f"+ Stage {script_name} completed successfully.") # Fix: Replaced ✓ with +
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"ERROR: Stage {script_name} failed. Return code: {e.returncode}")
        logging.error(f"STDOUT: {e.stdout}")
        logging.error(f"STDERR: {e.stderr}")
        return False

def main():
    logging.info("Starting the full pipeline execution...")
    
    # --- Stage 1: Find matching QP and MS PDF files and move them ---
    logging.info("Stage 1: Running QA_Match_Picker.py to find matching PDF pairs.")
    if not run_stage("QA_Match_Picker.py", RAW_DATA_DIR, MATCHED_PAIRS_DIR):
        logging.error("Pipeline terminated due to failure in Stage 1.")
        sys.exit(1)
        
    # --- Stage 2: Process each matched pair ---
    logging.info("Stage 2: Processing and merging each matched pair...")
    
    # Get the list of all matched pairs directories
    matched_pairs = [d for d in os.listdir(MATCHED_PAIRS_DIR) if os.path.isdir(os.path.join(MATCHED_PAIRS_DIR, d))]
    
    if not matched_pairs:
        logging.warning("No matched pairs found. Pipeline finished.")
        return

    for pair_dir in matched_pairs:
        pair_path = os.path.join(MATCHED_PAIRS_DIR, pair_dir)
        
        qp_file = next((f for f in os.listdir(pair_path) if '-QP-' in f or '_qp_' in f), None)
        ms_file = next((f for f in os.listdir(pair_path) if '-MS-' in f or '_ms_' in f), None)
        
        if not qp_file or not ms_file:
            logging.warning(f"Skipping pair '{pair_dir}' due to missing QP or MS file.")
            continue
            
        qp_pdf_path = os.path.join(pair_path, qp_file)
        ms_pdf_path = os.path.join(pair_path, ms_file)
        
        # Define temporary and final output paths for this pair
        qp_diagrams_dir = os.path.join(pair_path, "qp_diagrams")
        ms_diagrams_dir = os.path.join(pair_path, "ms_diagrams")
        qp_temp_json = os.path.join(pair_path, "qp_temp.json")
        ms_temp_json = os.path.join(pair_path, "ms_temp.json")
        output_ready_json = os.path.join(EXTRACTED_DATA_DIR, f"{pair_dir}_merged.json")

        logging.info(f"--- Processing pair: {pair_dir} ---")
        
        # --- Stage 2.1: Extract questions from QP ---
        qp_success = run_stage("extracted_questions_to_text.py", qp_pdf_path, qp_diagrams_dir, qp_temp_json)
        
        # CHECK IF QP JSON IS EMPTY (UNSTRUCTURED PAPER) AND SKIP
        if os.path.exists(qp_temp_json) and os.stat(qp_temp_json).st_size == 0:
            logging.warning(f"Skipping '{pair_dir}' as question paper seems to be unstructured (empty output).")
            continue
            
        if not qp_success:
            logging.error(f"Skipping '{pair_dir}' due to failure in question extraction.")
            continue
            
        # --- Stage 2.2: Extract marking scheme from MS ---
        ms_success = run_stage("marking_scheme_to_text_js.py", ms_pdf_path, ms_diagrams_dir, ms_temp_json)
        if not ms_success:
            logging.error(f"Skipping '{pair_dir}' due to failure in marking scheme extraction.")
            continue

        # --- Stage 2.3: Merge the extracted data ---
        merge_success = run_stage("merged_question_marking_scheme_js.py", qp_temp_json, ms_temp_json, output_ready_json)
        if not merge_success:
            logging.error(f"Failed to merge data for '{pair_dir}'.")
            continue
            
        # --- Cleanup temporary files (optional but good practice) ---
        os.remove(qp_temp_json)
        os.remove(ms_temp_json)
        shutil.rmtree(qp_diagrams_dir)
        shutil.rmtree(ms_diagrams_dir)
        logging.info(f"--- Successfully processed and cleaned up '{pair_dir}' ---")

if __name__ == "__main__":
    main()