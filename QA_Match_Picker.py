import os
import sys
import re
import shutil
import logging
from collections import defaultdict

# --- SETUP LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def find_and_move_matches(source_dir, dest_dir):
    """
    Finds matching question paper and marking scheme pairs and moves them
    to a destination folder.
    """
    if not os.path.exists(source_dir):
        logging.error(f"Error: Source directory not found at {source_dir}")
        return False
        
    logging.info(f"Scanning directory: {source_dir} for matching pairs...")
    
    file_groups = defaultdict(dict)
    
    # Regex to capture the unique part of the filename (e.g., '0610_m15_12')
    # This pattern is more flexible to handle different naming conventions.
    pattern = re.compile(r'(.+?(?:_m|_w|_s)\d{2}_[0-9a-z]{1,2}).*?_(qp|ms)')
    
    # Iterate through all files in the source directory
    for filename in os.listdir(source_dir):
        if not filename.lower().endswith(".pdf"):
            continue
            
        match = pattern.search(filename.lower())
        
        if match:
            unique_id = match.group(1)
            file_type = match.group(2)
            file_groups[unique_id][file_type] = filename
            
    if not file_groups:
        logging.info("No new matching question paper and marking scheme pairs found.")
        return True

    logging.info(f"Found {len(file_groups)} potential pairs. Moving files...")
    
    moved_count = 0
    
    # Process each potential pair
    for unique_id, files in file_groups.items():
        if 'qp' in files and 'ms' in files:
            qp_file = files['qp']
            ms_file = files['ms']
            
            # Create a unique folder for the pair
            # Use the full ID and increment a counter if needed
            pair_folder_name = f"Match_{unique_id.replace('/', '_')}"
            dest_pair_dir = os.path.join(dest_dir, pair_folder_name)
            
            # Ensure the directory is unique
            counter = 1
            while os.path.exists(dest_pair_dir):
                dest_pair_dir = os.path.join(dest_dir, f"{pair_folder_name}_{counter}")
                counter += 1
                
            os.makedirs(dest_pair_dir, exist_ok=True)
            
            # Move the files
            try:
                shutil.move(os.path.join(source_dir, qp_file), dest_pair_dir)
                shutil.move(os.path.join(source_dir, ms_file), dest_pair_dir)
                logging.info(f"+ Successfully moved pair: {qp_file} & {ms_file} to {dest_pair_dir}")
                moved_count += 1
            except Exception as e:
                logging.error(f"Error moving files for pair {unique_id}: {e}")
                
    logging.info(f"Finished. {moved_count} pairs were moved to '{dest_dir}'.")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python QA_Match_Picker.py <source_directory> <destination_directory>")
        sys.exit(1)
    
    source_folder = sys.argv[1]
    dest_folder = sys.argv[2]
    
    find_and_move_matches(source_folder, dest_folder)