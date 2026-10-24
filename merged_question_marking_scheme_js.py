# -*- coding: utf-8 -*-
"""
Merges a JSON file containing extracted questions with a JSON file containing
the corresponding marking scheme.

The script aligns each question part with its marking criteria and diagrams,
producing a single, comprehensive JSON file.

Usage:
    python merge_exams.py <path_to_questions_json> <path_to_markscheme_json> <output_json_path>

Example:
    python merge_exams.py aqa_exam.json aqa_markscheme.json aqa_complete.json
"""
import os
import sys
import json
import logging

# --- 1. SETUP LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- 2. HELPER FUNCTIONS ---

def load_json(file_path):
    """
    Loads JSON data from a file, with robust error handling.
    """
    try:
        if not os.path.exists(file_path):
            logging.error(f"Error: File not found at {file_path}")
            return None
        if os.stat(file_path).st_size == 0:
            logging.warning(f"Warning: JSON file is empty at {file_path}")
            return []

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logging.info(f"Successfully loaded data from {file_path}")
            return data

    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {file_path}. Please check file format.")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading {file_path}: {e}")
        return None

def create_markscheme_lookup(ms_data):
    """
    Converts the nested marking scheme list into a flat dictionary (hash map)
    for efficient O(1) lookups. The keys are question_ids.
    """
    ms_lookup = {}
    if not isinstance(ms_data, list):
        logging.error("Marking scheme data is not in the expected list format.")
        return ms_lookup

    for main_question in ms_data:
        # Ensure 'parts' exists and is a list before iterating
        if "parts" in main_question and isinstance(main_question.get("parts"), list):
            for part in main_question["parts"]:
                if "question_id" in part:
                    # Store the entire part object for a complete merge
                    ms_lookup[part["question_id"]] = part
    
    logging.info(f"Created a lookup map with {len(ms_lookup)} marking scheme parts.")
    return ms_lookup

def merge_exam_data(qp_json_path, ms_json_path, out_json_path):
    """
    Loads, merges, and saves the question paper and marking scheme data.
    """
    logging.info(f"Loading Question Paper data from: {qp_json_path}")
    qp_data = load_json(qp_json_path)
    if qp_data is None:
        logging.error("Failed to load question paper data. Aborting.")
        return False

    logging.info(f"Loading Marking Scheme data from: {ms_json_path}")
    ms_data = load_json(ms_json_path)
    if ms_data is None:
        logging.error("Failed to load marking scheme data. Aborting.")
        return False

    # Create an efficient lookup dictionary from the marking scheme data
    markscheme_lookup = create_markscheme_lookup(ms_data)
    if not markscheme_lookup:
        logging.warning("Marking scheme lookup map is empty. No matches will be found.")

    logging.info("Starting merge process: Linking marking scheme to questions...")
    match_count = 0
    miss_count = 0

    # Iterate through the question paper data and add the marking scheme
    for question_group in qp_data:
        for part in question_group.get("parts", []):
            qp_id = part.get("question_id")
            if qp_id:
                # Find the matching marking scheme using the lookup dictionary
                matching_ms = markscheme_lookup.get(qp_id)
                if matching_ms:
                    # Attach the entire marking scheme object
                    part["marking_scheme"] = matching_ms
                    match_count += 1
                else:
                    # Add a null value if no match is found for clarity
                    part["marking_scheme"] = None
                    miss_count += 1
                    logging.warning(f"-> No match found for question ID: {qp_id}")

    logging.info(f"Merge complete. Matched {match_count} parts. Could not find matches for {miss_count} parts.")

    # Save the merged data to the output file
    try:
        with open(out_json_path, 'w', encoding='utf-8') as f:
            json.dump(qp_data, f, indent=4, ensure_ascii=False)
        logging.info(f"✓ Successfully saved merged exam data to {out_json_path}")
        return True
    except Exception as e:
        logging.error(f"Error writing merged data to file: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python merge_exams.py <path_to_questions_json> <path_to_markscheme_json> <output_json_path>")
        sys.exit(1)

    questions_json_path = sys.argv[1]
    markscheme_json_path = sys.argv[2]
    output_json_path = sys.argv[3]

    if not merge_exam_data(questions_json_path, ms_json_path, out_json_path):
        sys.exit(1)