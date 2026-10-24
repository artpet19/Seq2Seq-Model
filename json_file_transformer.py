import json
import os
import sys
from typing import List, Dict

def transform_json_structure(input_data: Dict) -> Dict:
    """
    Transforms the JSON structure to nest sub-questions (3-digit question_numbers)
    under their corresponding main 2-digit question_numbers.

    Args:
        input_data (Dict): The original JSON data as a dictionary.

    Returns:
        Dict: The transformed JSON data.
    """
    transformed_questions = []
    
    # Create a dictionary to easily access main questions by their number (e.g., "01", "02")
    # This will hold the main question object and a list of its parts.
    main_questions_map = {}

    # First pass: Separate main questions from sub-questions and store main questions
    # in the map. Also, normalize part_id for consistent comparison.
    for q_obj in input_data["questions"]:
        q_num = q_obj["question_number"]
        if len(q_num) == 2:  # This is a main question (e.g., "01", "02")
            # Create a new structure for the main question.
            # We'll re-add its own parts later if they don't match the sub-question pattern.
            main_questions_map[q_num] = {
                "question_number": q_num,
                "parts": [] # This will hold the main question's own parts and then nested sub-parts
            }
            # Add the original parts of the main question to its `parts` list
            # For "01", this will be the initial introductory text part_id "01"
            main_questions_map[q_num]["parts"].extend(q_obj["parts"])
        else:
            # Sub-questions will be processed in the second pass
            pass

    # Second pass: Iterate through all questions again to nest sub-questions
    for q_obj in input_data["questions"]:
        q_num = q_obj["question_number"]
        
        if len(q_num) > 2:  # This is a sub-question (e.g., "011", "012", "021")
            # Extract the prefix for grouping (e.g., "01" from "011", "02" from "021")
            main_q_prefix = q_num[:2]

            if main_q_prefix in main_questions_map:
                # Find the main question object
                main_q_obj = main_questions_map[main_q_prefix]
                
                # The user specified that nesting should happen at the *last* part_id key
                # within the main question's 'parts' list if there are multiple '01' part_ids.
                # This logic assumes the '01' 'part_id' for the main question is the
                # introductory text and that sub-parts should follow it.
                
                # Check if the main question already has a part matching its own question_number
                # e.g., question_number "01" having a part with "part_id": "01"
                target_part_found = False
                for part_idx, part in enumerate(main_q_obj["parts"]):
                    # If we find a part_id that matches the main question number, and it's the last one,
                    # we target it for nesting. If there are multiple, the last one found will be the target.
                    if part["part_id"] == main_q_prefix:
                        # Ensure the 'nested_parts' list exists for this target part
                        if "nested_parts" not in part:
                            part["nested_parts"] = []
                        
                        # Add all parts of the current sub-question object to the 'nested_parts'
                        # of the target part in the main question.
                        part["nested_parts"].extend(q_obj["parts"])
                        target_part_found = True
                        break # Break after adding to the first matching part_id.
                              # If the user meant 'last occurrence of the same part_id',
                              # then this loop would need to continue and override 'target_part'.
                              # Given the example "01","01","01" for different part_id keys,
                              # this implies we want to append to THE specific part_id: "01".
                              # The current interpretation is that the main "01" question has a
                              # primary part_id "01" within its own "parts" list, and subsequent
                              # three-digit question numbers (011, 012 etc) should be nested there.
                              # To handle multiple "01" part_ids within a question's "parts",
                              # we need to ensure we target the *last* one if that's the intent.
                              # Let's adjust to target the last "01" part_id if multiple exist.

                # If no specific part_id matching the main question was found in its own parts,
                # or if the main question itself had no initial parts, append to the main question's parts directly.
                # However, based on the prompt "nesting should happen at the last part_id key",
                # it implies existing parts are the target.

                # To ensure it always nests under the LAST part_id matching the prefix within the main question,
                # we need to find that last part.
                last_matching_part_index = -1
                for i, part in enumerate(main_q_obj["parts"]):
                    if part["part_id"] == main_q_prefix:
                        last_matching_part_index = i
                
                if last_matching_part_index != -1:
                    target_part = main_q_obj["parts"][last_matching_part_index]
                    if "nested_parts" not in target_part:
                        target_part["nested_parts"] = []
                    target_part["nested_parts"].extend(q_obj["parts"])
                else:
                    # Fallback: if no specific '01' part_id found,
                    # just append the sub-question to the main question's parts.
                    # This scenario might indicate the parsing logic needs further refinement
                    # if such main questions are always supposed to have a matching part_id.
                    # For now, let's assume the presence of main_q_prefix in main_questions_map
                    # implies a target part_id matching main_q_prefix.
                    print(f"WARNING: Main question {main_q_prefix} has no part_id matching itself to nest under. Appending sub-question {q_num} to main parts.")
                    main_q_obj["parts"].extend(q_obj["parts"])
            else:
                # If a sub-question's prefix doesn't match any main question,
                # it means it's an orphaned sub-question or a typo/parsing error.
                # For now, we'll keep it as a top-level question in the output.
                transformed_questions.append(q_obj)
        else:
            # If it's a main question (len == 2), it's already in main_questions_map.
            # We add it to the final list in the third pass to ensure correct order.
            pass

    # Third pass: Add all main questions (with their potentially nested sub-parts)
    # and any un-nested sub-questions (orphaned) to the final list, maintaining original order.
    # We iterate through the original questions to preserve the order of main questions.
    added_main_q_nums = set()
    for q_obj in input_data["questions"]:
        q_num = q_obj["question_number"]
        if len(q_num) == 2 and q_num not in added_main_q_nums:
            # Add the main question with its aggregated parts
            transformed_questions.append(main_questions_map[q_num])
            added_main_q_nums.add(q_num)
        elif len(q_num) > 2:
            # If it was an orphaned sub-question (not nested), add it here.
            # This handles cases where a sub-question's prefix doesn't have a matching 2-digit main question.
            main_q_prefix = q_num[:2]
            if main_q_prefix not in main_questions_map:
                transformed_questions.append(q_obj)

    return {"exam_code": input_data["exam_code"], "questions": transformed_questions}

import os
import json
import sys

def transform_json_structure(data):
    # Placeholder transformation logic
    # Replace this with actual transformation logic as needed
    return data

def process_json_folder(input_dir, output_dir):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Loop through all JSON files in the input directory
    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            input_json_path = os.path.join(input_dir, filename)

            try:
                with open(input_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Perform the transformation
                transformed_data = transform_json_structure(data)

                # Define output file path
                output_filename = f"transformed_{filename}"
                output_path = os.path.join(output_dir, output_filename)

                # Save the transformed JSON
                with open(output_path, 'w', encoding='utf-8') as f_out:
                    json.dump(transformed_data, f_out, indent=2)

                print(f"✓ Transformation complete. Output saved to: {output_path}")

            except Exception as e:
                print(f"Error processing {filename}: {e}")

# Main execution logic
if __name__ == "__main__":
    if len(sys.argv) == 3:
        input_dir = sys.argv[1]
        output_dir = sys.argv[2]
    else:
        print("Usage: python json_file_transformer.py <input_json_folder> <output_directory>")
        print("Incorrect number of arguments provided. Falling back to hardcoded defaults for testing.")
        input_dir = "Ready_Dataset"
        output_dir = "Ready_Dataset_Transformed_Output"

    process_json_folder(input_dir, output_dir)

