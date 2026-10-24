import os
import json
import re
import sys
from collections import defaultdict
from typing import List, Dict, Any

def sanitize_json_string(json_str: str) -> str:
    """Removes invalid control characters from a string to prevent JSON parsing errors."""
    return re.sub(r'[\x00-\x1F\x7F]', '', json_str)

def restructure_questions(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Restructures a flat list of question parts into a nested structure
    of questions with their corresponding parts.
    """
    restructured_data = defaultdict(lambda: {"question_number": "", "parts": []})

    for part in data:
        part_id = part.get("question_id", "")
        if not part_id:
            continue
            
        # Extract the main question number (e.g., '1' from '1a' or '1(a)')
        main_q_match = re.match(r'^(\d+)', part_id)
        if main_q_match:
            main_q_number = int(main_q_match.group(1))
            
            # Use the main question number as the key
            restructured_data[main_q_number]["question_number"] = main_q_number
            restructured_data[main_q_number]["parts"].append(part)

    # Sort the final list of questions numerically
    sorted_questions = sorted(restructured_data.values(), key=lambda x: x["question_number"])
    
    return sorted_questions

def process_json_files(input_path: str, output_dir: str):
    """Processes a single JSON file or a folder of JSON files."""
    os.makedirs(output_dir, exist_ok=True)
    
    if os.path.isdir(input_path):
        # Process all JSON files in the directory
        for filename in os.listdir(input_path):
            if filename.endswith(".json"):
                file_path = os.path.join(input_path, filename)
                process_single_file(file_path, output_dir, filename)
    else:
        # Process a single specified file
        filename = os.path.basename(input_path)
        process_single_file(input_path, output_dir, filename)

def process_single_file(input_path: str, output_dir: str, filename: str):
    """Loads, sanitizes, restructures, and saves a single JSON file."""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            sanitized_content = sanitize_json_string(raw_content)
            data = json.loads(sanitized_content)
            
        transformed_data = restructure_questions(data)
        
        output_filename = f"restructured_{filename}"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f_out:
            json.dump(transformed_data, f_out, indent=2)
            
        print(f"✓ Transformation complete. Output saved to: {output_path}")
        
    except FileNotFoundError:
        print(f"Error: File not found at {input_path}.")
    except json.JSONDecodeError as e:
        print(f"Error processing {filename}: Invalid JSON format. Details: {e}")
    except Exception as e:
        print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python enhance_data.py <input_path_to_json_file_or_folder> <output_directory>")
        sys.exit(1)
        
    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    process_json_files(input_path, output_dir)