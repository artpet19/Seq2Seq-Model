import os
import json
import random
import sys
from typing import List, Dict, Any

def process_and_split_data(input_folder: str, output_root: str):
    """
    Processes all JSON files in the input folder, flattens the data, and splits
    it into train, test, validation, and test_labels directories.
    
    Args:
        input_folder (str): The path to the folder containing input JSON files.
        output_root (str): The root directory where the new split folders will be created.
    """
    print(f"Starting data splitting process from {input_folder}...")

    # Define the output folders based on the output root.
    train_folder = os.path.join(output_root, "train")
    test_folder = os.path.join(output_root, "test")
    validation_folder = os.path.join(output_root, "validation")
    test_labels_folder = os.path.join(output_root, "test_labels")

    # Create all output directories if they don't exist.
    for folder in [train_folder, test_folder, validation_folder, test_labels_folder]:
        os.makedirs(folder, exist_ok=True)

    # Define the split ratios for the dataset.
    train_ratio = 0.70
    validation_ratio = 0.10
    
    for fname in os.listdir(input_folder):
        if fname.endswith(".json"):
            input_path = os.path.join(input_folder, fname)

            try:
                with open(input_path, "r", encoding="utf-8") as f_in:
                    data = json.load(f_in)
                
                # Flatten the list of questions and their parts into a single list of entries.
                flattened_entries = []
                for question in data:
                    for part in question.get("parts", []):
                        flattened_entries.append(part)

                # Shuffle the flattened data to ensure a random distribution.
                random.shuffle(flattened_entries)
                
                # Calculate the split indices.
                total_entries = len(flattened_entries)
                train_split = int(total_entries * train_ratio)
                validation_split = train_split + int(total_entries * validation_ratio)

                # Split the data into respective lists.
                train_data = flattened_entries[:train_split]
                validation_data = flattened_entries[train_split:validation_split]
                test_data = flattened_entries[validation_split:]
                
                # Create the test_labels data by extracting the marking scheme and diagrams.
                test_labels_data = [
                    {
                        "question_id": item.get("question_id"),
                        "marking_scheme": item.get("marking_scheme"),
                        "diagrams": item.get("diagrams", [])
                    }
                    for item in test_data
                ]

                # Create the test data without the marking scheme.
                test_data_no_labels = [
                    {k: v for k, v in d.items() if k != 'marking_scheme'}
                    for d in test_data
                ]
                
                # Save the split data to the respective folders.
                with open(os.path.join(train_folder, fname), "w", encoding="utf-8") as f_out:
                    json.dump(train_data, f_out, indent=2)
                
                with open(os.path.join(validation_folder, fname), "w", encoding="utf-8") as f_out:
                    json.dump(validation_data, f_out, indent=2)

                with open(os.path.join(test_folder, fname), "w", encoding="utf-8") as f_out:
                    json.dump(test_data_no_labels, f_out, indent=2)
                
                with open(os.path.join(test_labels_folder, fname), "w", encoding="utf-8") as f_out:
                    json.dump(test_labels_data, f_out, indent=2)
                
                print(f"✓ Processed and split: {fname}")
            except Exception as e:
                print(f"Error processing file {fname}: {e}")

    print("\n✓ All data split and saved to the output folders.")

# --- Main Execution ---
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python final_dataset_split.py <input_folder> <output_root_folder>")
        sys.exit(1)
        
    input_folder = sys.argv[1]
    output_root = sys.argv[2]
    
    process_and_split_data(input_folder, output_root)
    
