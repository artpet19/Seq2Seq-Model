import os
import json
import re
import sys
from typing import List, Dict, Any

# This script is designed to take the restructured JSON data and
# prepare it for use in a machine learning pipeline.

def process_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a single data entry (a dictionary) from the input JSON file.
    This function extracts and structures the data for machine learning.
    
    Args:
        entry (dict): A dictionary representing a single data entry (a question part).
        
    Returns:
        dict: The processed dictionary with cleaned text and a list of image paths,
              or None if the entry is invalid.
    """
    processed = {}
    
    # Extract and clean the question text.
    # The 'text' key contains the question's content.
    question_text = entry.get("text")
    if question_text and isinstance(question_text, str):
        processed["question_text"] = re.sub(r'\s+', ' ', question_text).strip()
    
    # Extract and clean the marking scheme text.
    # The 'marking_scheme' key is a dictionary containing the MS content.
    marking_scheme = entry.get("marking_scheme")
    if marking_scheme and isinstance(marking_scheme, dict):
        ms_text = marking_scheme.get("text")
        if ms_text and isinstance(ms_text, str):
            processed["marking_scheme_text"] = re.sub(r'\s+', ' ', ms_text).strip()
    
    # Handle the 'visuals' (diagrams, graphs, tables).
    # We will only store the file paths for later use by the model.
    visuals = entry.get("diagrams", [])
    if visuals and isinstance(visuals, list):
        # We store the entire list of diagram metadata for context
        processed["visuals"] = visuals
    
    # Add other key metadata for training and evaluation purposes.
    processed["question_id"] = entry.get("question_id")
    processed["page_number"] = entry.get("page")
    
    # Return the processed dictionary only if it has valid content.
    if any(value for value in processed.values() if value is not None):
        return processed
    return None

def process_files_in_folder(input_folder: str, output_folder: str):
    """
    Main function to orchestrate the data processing pipeline.
    It iterates through all JSON files in the input folder, processes them,
    and saves the output to the specified folder.
    
    Args:
        input_folder (str): The path to the folder containing input JSON files.
        output_folder (str): The path to the folder where processed files will be saved.
    """
    os.makedirs(output_folder, exist_ok=True)
    
    for fname in os.listdir(input_folder):
        if fname.endswith(".json"):
            input_path = os.path.join(input_folder, fname)
            output_path = os.path.join(output_folder, f"ready_{fname}")

            try:
                with open(input_path, "r", encoding="utf-8") as f_in:
                    data = json.load(f_in)
                
                # We expect the data to be a list of questions, each with a 'parts' list.
                processed_entries = []
                for question in data:
                    for part in question.get("parts", []):
                        processed_entry = process_entry(part)
                        if processed_entry:
                            processed_entries.append(processed_entry)
                
                with open(output_path, "w", encoding="utf-8") as f_out:
                    json.dump(processed_entries, f_out, indent=2)
                
                print(f"✓ Processed and saved: {fname} -> ready_{fname}")
            except Exception as e:
                print(f"Error processing file {fname}: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python enhance_data_for_ml.py <input_folder> <output_folder>")
        sys.exit(1)
        
    input_folder = sys.argv[1]
    output_folder = sys.argv[2]
    
    process_files_in_folder(input_folder, output_folder)
    print("\n✓ All data processed and saved to the output folder.")