import re
import os
import json
import sys
from typing import List, Dict

# ────────────────────────────────────────────────────────────────
#   CONFIG (These are now arguments, not hardcoded)
# ────────────────────────────────────────────────────────────────
# qp_text_file, qp_ocr_file, qp_diagram_dir, ms_json_file, output_ready_dir
# These will be populated from sys.argv if the script is run with arguments
# For local testing, you can uncomment these or run the script with the paths.
qp_text_file    = "Out_put/Match_001_AQA-8464B1F-JUN22/extracted_qp_text.txt"
qp_ocr_file     = "Out_put/Match_001_AQA-8464B1F-JUN22/extracted_qp_ocr.txt"
qp_diagram_dir  = "Out_put/Match_001_AQA-8464B1F-JUN22/qp_diagrams"
ms_json_file    = "Out_put/Match_001_AQA-8464B1F-JUN22/extracted_marking_scheme.json"
output_ready_dir  = "Ready_dataset"
# ────────────────────────────────────────────────────────────────

# Load text from a file
def load_text(path: str) -> str:
    """Loads text content from a specified file path."""
    with open(path, encoding="utf-8") as f:
        return f.read()

def load_marking_scheme(src):
    """Loads marking scheme data from a JSON file or directly from a dict."""
    if isinstance(src, dict):
        return src
    with open(src, encoding="utf-8") as f:
        return json.load(f)

def parse_ocr_file(ocr_file: str) -> Dict[str, Dict]:
    """
    Parses OCR text file to extract image information including OCR text,
    page number, and bounding boxes.
    Returns a dictionary mapping image filenames to their extracted data.
    """
    raw = load_text(ocr_file)
    ocr_data_map = {}
    
    # Corrected regex with raw string literals for proper interpretation of escape sequences
    block_pattern = re.compile(
        r"(?m)^(?P<image_file>page_\d+_img_\d+\.png):\n"
        r"\s*OCR Text\s*:\s*(?P<ocr_text>.*?)\n"
        r"\s*Page\s*:\s*(?P<page_number>\d+)\n"
        r"\s*PDF BBox\s*:\s*\((?P<pdf_bbox>[^)]+)\)\n"
        r"\s*Pixel BBox\s*:\s*\((?P<pixel_bbox>[^)]+)\)",
        re.DOTALL,
    )

    for match in block_pattern.finditer(raw):
        image_file = match.group("image_file")
        ocr_text = match.group("ocr_text").strip()
        page_number = int(match.group("page_number"))
        
        # Convert bbox strings to tuples of floats/ints
        pdf_bbox_str = match.group("pdf_bbox")
        pdf_bbox = tuple(float(x.strip()) for x in pdf_bbox_str.split(','))
        
        pixel_bbox_str = match.group("pixel_bbox")
        pixel_bbox = tuple(int(x.strip()) for x in pixel_bbox_str.split(','))
        
        ocr_data_map[image_file] = {
            "ocr_text": ocr_text,
            "page_number": page_number,
            "pdf_bbox": pdf_bbox,
            "pixel_bbox": pixel_bbox,
        }
    return ocr_data_map

def find_diagram_in_text(diagram_info, text_content):
    """
    Placeholder function for finding diagram references within text.
    Currently, it simply returns the diagram_info itself, as detailed
    text-to-diagram linkage based on content requires more advanced logic.
    """
    # This function needs more sophisticated logic if diagrams are truly embedded
    # into the text and not just linked by a bounding box.
    # For now, we'll just check if the OCR text from the diagram appears in the main text.
    # A more robust solution would involve checking bounding box overlaps with text lines.
    return diagram_info # Returning diagram_info itself if no specific linkage is found within text

def assign_diagrams_to_questions(parsed_questions, ocr_data_map, qp_diagram_dir):
    """
    Assigns OCR data/diagrams to the closest question part based on page number.
    The vertical proximity check has been removed as PDF bbox for question parts
    is not available and estimated_y (character index) is not comparable with PDF coordinates.
    Also includes the full path to the diagram image.
    """
    # Create a mapping of page number to a list of diagrams on that page
    diagrams_by_page = {}
    for img_filename, diagram_info in ocr_data_map.items():
        page = diagram_info["page_number"]
        if page not in diagrams_by_page:
            diagrams_by_page[page] = []
        
        diagram_entry = {
            "image_file": img_filename,
            "ocr_text": diagram_info["ocr_text"],
            "page_number": diagram_info["page_number"],
            "pdf_bbox": diagram_info["pdf_bbox"],
            "pixel_bbox": diagram_info["pixel_bbox"],
            "path_to_image": os.path.join(qp_diagram_dir, img_filename) # Add full path
        }
        diagrams_by_page[page].append(diagram_entry)

    for q_num, q_parts in parsed_questions.items():
        for part in q_parts:
            part_page_0_indexed = part.get("original_page_idx") 
            if part_page_0_indexed is None:
                continue

            # Convert to 1-indexed page number for comparison with diagram page numbers
            part_page_1_indexed = part_page_0_indexed + 1

            # Initialize diagrams list for this part
            part["diagrams"] = []

            # Add diagrams found on the same page from OCR data
            if part_page_1_indexed in diagrams_by_page:
                # Add a copy of the list to avoid modifying the original list in diagrams_by_page
                part["diagrams"].extend(list(diagrams_by_page[part_page_1_indexed])) 
            
            # Note: Final sorting will happen in merge_data after also pulling diagrams from MS
    return parsed_questions


def parse_questions_from_text(qp_text_content):
    """
    Parses question parts from the raw QP text, extracting question IDs,
    body text, and estimating page numbers.
    It now correctly handles spaces in question numbers and normalizes them.
    """
    print(f"DEBUG: Raw QP text length: {len(qp_text_content)}")
    print(f"DEBUG: Raw QP text (repr, first 500 chars):\n{repr(qp_text_content[:500])}")

    # Normalize newlines and replace common non-newline whitespace characters
    qp_text_content_processed = qp_text_content.replace('\r\n', '\n').replace('\r', '\n') # Handles CRLF and CR
    # Replace any sequence of one or more non-newline whitespace characters with a single space.
    qp_text_content_processed = re.sub(r'[^\S\n]+', ' ', qp_text_content_processed) 

    # Strip leading/trailing whitespace from each line, then rejoin.
    # This ensures `^` correctly matches the start of meaningful content on a line.
    lines = qp_text_content_processed.split('\n')
    qp_text_content_processed = '\n'.join([line.strip() for line in lines])
    # Add an extra newline at the end to ensure the last question can be matched by lookahead
    qp_text_content_processed += '\n' 
    

    # Further cleaning: remove any non-ASCII characters that are not part of common text or numbers
    # This targets potential hidden characters from OCR that are not whitespace.
    # Keep printable ASCII (32-126) and newlines.
    qp_text_content_processed = "".join(c for c in qp_text_content_processed if 32 <= ord(c) <= 126 or c == '\n')


    print(f"DEBUG: Preprocessed QP text length: {len(qp_text_content_processed)}")
    print(f"DEBUG: Preprocessed QP text (repr, first 500 chars):\n{repr(qp_text_content_processed[:500])}")

    # --- DIAGNOSTIC ADDITIONS (retained for initial debugging context) ---
    # Check if the problematic string exists after preprocessing
    check_string = "\n0 1" 
    first_occurrence_idx = qp_text_content_processed.find(check_string)
    if first_occurrence_idx != -1:
        print(f"DEBUG: Found '{repr(check_string)}' at index {first_occurrence_idx}")
        start_idx = max(0, first_occurrence_idx - 50)
        end_idx = min(len(qp_text_content_processed), first_occurrence_idx + len(check_string) + 50)
        context_string = qp_text_content_processed[start_idx:end_idx]
        print(f"DEBUG: Context around '{repr(check_string)}':\n{repr(context_string)}")
        print("DEBUG: Character codes in context:")
        for i, char in enumerate(context_string):
            print(f"  {i + start_idx}: '{repr(char)}' (ord: {ord(char)})")
        
        # --- NEW TEST: Direct re.match on the line containing the first question ---
        lines_list = qp_text_content_processed.split('\n')
        line_with_question_found = None
        line_num_with_question = -1
        for i, line in enumerate(lines_list):
            if re.match(r"^0\s*1", line): 
                line_with_question_found = line
                line_num_with_question = i
                break
        
        if line_with_question_found:
            print(f"DEBUG: Testing re.match on line {line_num_with_question}: {repr(line_with_question_found[:100])}")
            print("DEBUG: Character codes at start of line_with_question_found:")
            for i, char in enumerate(line_with_question_found[:10]):
                print(f"  {i}: '{repr(char)}' (ord: {ord(char)})")
            
            print(f"DEBUG: Raw bytes of line_with_question_found: {line_with_question_found.encode('utf-8')}")


            # Corrected to raw string
            test_pattern_for_match = re.compile(r"^(?P<q_num_raw>\d\s*\d(?:\s*\.\s*\d{0,2})?)", re.MULTILINE) 
            match_test_result = test_pattern_for_match.match(line_with_question_found)
            if match_test_result:
                print(f"DEBUG: re.match test successful! Matched: '{match_test_result.group(0)}' Raw Q Num: '{match_test_result.group('q_num_raw')}'")
            else:
                print("DEBUG: re.match test FAILED on the exact line containing '0 1'.")
        else:
            print("DEBUG: Could not find a line explicitly starting with '0 1' in processed text for re.match test.")
        # --- END NEW TEST ---

    else:
        print(f"DEBUG: Did NOT find '{repr(check_string)}' in preprocessed text.")

    # --- SIMPLIFIED REGEX TEST ---
    # Corrected to raw string
    simple_test_pattern = re.compile(r"(?m)^\s*\d\s*\d") 
    simple_matches = list(simple_test_pattern.finditer(qp_text_content_processed))
    print(f"DEBUG: Simple regex test ('^\s*\d\s*\d') found {len(simple_matches)} matches.")
    if simple_matches:
        for i, m in enumerate(simple_matches[:5]): 
            print(f"DEBUG: Simple match {i}: '{m.group(0)}' at index {m.start()}")
            start_idx = max(0, m.start() - 10)
            end_idx = min(len(qp_text_content_processed), m.end() + 10)
            print(f"DEBUG:   Context: '{repr(qp_text_content_processed[start_idx:end_idx])}'")
    # --- END SIMPLIFIED REGEX TEST ---

    # Main regex to find question parts. Corrected to raw string
    question_part_pattern = re.compile(
        r"(?m)^\s*(?P<q_num_raw>\d\s*\d(?:\s*\.\s*\d{0,2})?)\s*(?P<body>.*?)" 
        r"(?=\n^\s*(?:\d\s*\d(?:\s*\.\s*\d{0,2})?|---PAGE BREAK---)|\Z)", 
        re.DOTALL
    )

    print(f"DEBUG: Full Regex pattern: '{question_part_pattern.pattern}'")

    parsed_questions = {}
    
    # Calculate page breaks to determine original_page_idx
    page_breaks_indices = [idx for idx, char in enumerate(qp_text_content_processed) if qp_text_content_processed.startswith("---PAGE BREAK---", idx)]
    
    found_matches = 0
    for m in question_part_pattern.finditer(qp_text_content_processed):
        found_matches += 1
        q_id_raw = m.group("q_num_raw").strip()
        # Ensure q_id only contains digits for reliable integer conversion and matching
        q_id = "".join(c for c in q_id_raw if c.isdigit())
        
        body_text = m.group("body").strip()
        start_char_pos = m.start() # Position of the start of the match

        current_page_idx = 0
        for i, pb_pos in enumerate(page_breaks_indices):
            if start_char_pos > pb_pos:
                current_page_idx = i + 1
            else:
                break
        
        dummy_bbox = (0, 0, 0, 0)
        estimated_y = start_char_pos 

        part_entry = {
            "part_id": q_id,
            "body": body_text,
            "global_text_pos_start": start_char_pos, 
            "original_page_idx": current_page_idx, 
            "pdf_bbox": dummy_bbox,
            "estimated_y": estimated_y,
            "diagrams": [] # Initialize empty list for diagrams
        }
        
        main_q_num = q_id.split('.')[0] 
        parsed_questions.setdefault(main_q_num, []).append(part_entry)
            
    print(f"DEBUG: parse_questions_from_text (full regex) found {found_matches} matches.")
    if not parsed_questions:
        print("DEBUG: No questions were successfully parsed by the full regex.")
    return parsed_questions


def merge_data(qp_text_file, qp_ocr_file, qp_diagram_dir, ms_json_file, out_json_dir):
    """
    Main function to load, parse, and merge data from question paper text,
    OCR results, and the marking scheme.
    """
    print(f"Loading QP text from: {qp_text_file}")
    qp_text_content = load_text(qp_text_file)
    print(f"Loading OCR data from: {qp_ocr_file}")
    qp_ocr_data = parse_ocr_file(qp_ocr_file) 
    print(f"Loading Marking Scheme from: {ms_json_file}")
    marking_scheme = load_marking_scheme(ms_json_file)

    print("Parsing questions from QP text...")
    grouped_questions = parse_questions_from_text(qp_text_content)
    
    print("Assigning diagrams to questions...")
    # First pass: assign diagrams found in OCR data to question parts
    assign_diagrams_to_questions(grouped_questions, qp_ocr_data, qp_diagram_dir)

    # Flatten the marking scheme into a list for easier lookup
    ms_list = []
    for q_num_ms in marking_scheme.values():
        ms_list.extend(q_num_ms)

    print("Linking marking scheme to questions...")
    for main_q, parts in grouped_questions.items():
        for part in parts:
            pid = part["part_id"] # This is like '011', '012', etc.
            
            # Find the corresponding marking scheme entry
            ms_entry = None
            for m in ms_list:
                ms_item_part_normalized = "".join(c for c in m["part"] if c.isdigit())
                
                if ms_item_part_normalized == pid:
                    ms_entry = m
                    break 

            if ms_entry:
                # If the MS entry has its own diagrams, append them to the part's diagrams
                if "diagrams" in ms_entry and ms_entry["diagrams"]:
                    part["diagrams"].extend(ms_entry["diagrams"])
                    del ms_entry["diagrams"] # Remove from MS entry to prevent nesting
                
                part["marking_scheme"] = ms_entry
                print(f"    Matched MS for QP Part ID: {pid} with MS Entry Part: {ms_entry['part']}") 
            else:
                part["marking_scheme"] = {}
                print(f"    No MS match found for QP Part ID: {pid}") 
            
            # Sort all collected diagrams for this part by their top Y-coordinate (pdf_bbox[1])
            # This ensures diagrams are ordered vertically on the page.
            if part["diagrams"]:
                part["diagrams"].sort(key=lambda d: d["pdf_bbox"][1])

            # Clean up temporary keys before final output
            part.pop("global_text_pos_start", None)
            part.pop("estimated_y", None) 
            part["page_number"] = part.pop("original_page_idx") + 1 

    result = {
        "exam_code": "AQA-UNKNOWN", 
        "questions": []
    }

    match_name_from_path = os.path.basename(os.path.dirname(qp_text_file))
    if match_name_from_path.startswith("Match_") and len(match_name_from_path.split('_')) > 2:
        result["exam_code"] = '-'.join(match_name_from_path.split('_')[2:])


    # Sort questions by their main question number
    for qnum in sorted(grouped_questions.keys(), key=lambda x: int(x)):
        # Sort parts within each question by their part_id for consistent order
        sorted_parts = sorted(grouped_questions[qnum], key=lambda x: x["part_id"])
        result["questions"].append({
            "question_number": qnum,
            "parts": sorted_parts
        })

    os.makedirs(out_json_dir, exist_ok=True)
    
    output_filename = f"merged_data_{result['exam_code']}.json" 
    output_path = os.path.join(out_json_dir, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"✓ Merged data written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python merged_question_marking_scheme_js.py <qp_text_file> <qp_ocr_file> <qp_diagram_dir> <ms_json_file> <output_ready_dir>")
        print("\nUsing hardcoded paths for demonstration/testing.")
        qp_text_file    = "Out_put/Match_001_AQA-8464B1F-JUN22/extracted_qp_text.txt"
        qp_ocr_file     = "Out_put/Match_001_AQA-8464B1F-JUN22/extracted_qp_ocr.txt"
        qp_diagram_dir  = "Out_put/Match_001_AQA-8464B1F-JUN22/qp_diagrams"
        ms_json_file    = "Out_put/Match_001_AQA-8464B1F-JUN22/extracted_marking_scheme.json"
        output_ready_dir  = "Ready_dataset"
        
        print(f"QP Text: {qp_text_file}")
        print(f"OCR: {qp_ocr_file}")
        print(f"Diagrams: {qp_diagram_dir}")
        print(f"MS: {ms_json_file}")
        print(f"Output Dir: {output_ready_dir}\n")
    else:
        qp_text_file = sys.argv[1]
        qp_ocr_file = sys.argv[2]
        qp_diagram_dir = sys.argv[3]
        ms_json_file = sys.argv[4]
        output_ready_dir = sys.argv[5]

    merge_data(qp_text_file, qp_ocr_file, qp_diagram_dir, ms_json_file, output_ready_dir)


# This script merges question paper text, OCR results, and marking scheme data into a structured JSON format.
# It handles parsing, diagram assignment, and final output generation.
# The output JSON is structured to facilitate easy access to question parts and their associated marking scheme.
# The script can be run with command line arguments or with hardcoded paths for testing purposes.