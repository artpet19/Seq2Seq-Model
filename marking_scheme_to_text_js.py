# -*- coding: utf-8 -*-
"""
Processes a PDF marking scheme to extract question answers and any associated
diagrams/images, embedding them as Base64 strings into a structured JSON file.

Usage:
    python process_markscheme.py <path_to_pdf> <diagrams_output_dir> <json_output_path>

Example:
    python process_markscheme.py AQA-84654H-MS-JUN23.pdf ./ms_images aqa_markscheme.json
"""
import os
import sys
import json
import logging
import re
import fitz  # PyMuPDF
import base64

# --- 1. SETUP LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --- 2. HELPER FUNCTIONS ---

def encode_image_to_base64(image_path):
    """Reads an image file from disk and returns its Base64 encoded string."""
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except IOError as e:
        logging.error(f"Could not read image file for encoding {image_path}: {e}")
        return None

def extract_images_from_pdf(pdf_path, output_dir):
    """
    Extracts all images from a PDF, saves them, and returns a dictionary
    mapping page numbers to a list of image file paths.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"Created directory: {output_dir}")

    images_by_page = {}
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logging.error(f"Failed to open PDF {pdf_path}: {e}")
        return images_by_page

    for page_num in range(len(doc)):
        page_images = []
        for img_index, img in enumerate(doc.get_page_images(page_num)):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                image_filename = f"image_p{page_num + 1}_{img_index}.png"
                image_path = os.path.join(output_dir, image_filename)

                if pix.n - pix.alpha >= 4: # Handle CMYK
                    pix_rgb = fitz.Pixmap(fitz.csRGB, pix)
                    pix_rgb.save(image_path)
                else:
                    pix.save(image_path)
                page_images.append(image_path)
            except Exception as e:
                logging.warning(f"Could not extract image on page {page_num + 1} with xref {xref}: {e}")

        if page_images:
            images_by_page[page_num + 1] = page_images

    doc.close()
    total_images = sum(len(v) for v in images_by_page.values())
    logging.info(f"Extracted {total_images} images to '{output_dir}'.")
    return images_by_page

def clean_text(text):
    """Removes extra whitespace and consolidates text into a single line."""
    return ' '.join(text.strip().split())

def parse_marking_scheme_text(full_text):
    """
    Parses the full text of a marking scheme to identify question numbers and their content.
    """
    # Regex to find question IDs at the start of a line
    question_pattern = re.compile(
        # AQA Style (e.g., "01.1", "04.2")
        r"^\s*(?P<aqa_id>0\d\.\d+)|"
        # Cambridge Style (e.g., "1 (a)", "4 (c) (i)")
        r"^\s*(?P<main>\d+)\s*\((?P<part_a>\w+)\)(?:\s*\((?P<part_b>[\w\d]+)\))?"
    )
    # Pattern for floating sub-parts (e.g., "(b)", "(ii)")
    sub_part_pattern = re.compile(r"^\s*\(([\w\d]+)\)")

    lines = full_text.split('\n')
    marking_items = []
    current_item = None
    last_main_q_num = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        match = question_pattern.match(line_stripped)
        sub_match = sub_part_pattern.match(line_stripped)
        new_item_detected = False
        item_id = None

        if match:
            new_item_detected = True
            if match.group('aqa_id'):
                item_id = match.group('aqa_id')
                last_main_q_num = item_id.split('.')[0]
            else:
                main, p_a, p_b = match.group('main'), match.group('part_a'), match.group('part_b')
                item_id_parts = [p for p in [main, p_a, p_b] if p]
                item_id = ".".join(item_id_parts)
                last_main_q_num = main
        elif sub_match and last_main_q_num:
            # This is a sub-part without a main number, use context
            new_item_detected = True
            item_id = f"{last_main_q_num}.{sub_match.group(1)}"
        elif re.match(r"^\s*(\d+)\s+\(a\)", line_stripped):
             # Catches cases where a new main question starts (e.g. "1 (a)")
             last_main_q_num = re.match(r"^\s*(\d+)", line_stripped).group(1)

        if new_item_detected:
            if current_item:
                current_item['content'] = clean_text(current_item['content'])
                marking_items.append(current_item)
            current_item = {"question_id": item_id, "content": line_stripped}
        elif current_item:
            current_item['content'] += " " + line

    if current_item: # Append the last item
        current_item['content'] = clean_text(current_item['content'])
        marking_items.append(current_item)

    return marking_items

def find_item_page(pdf_doc, item_content):
    """Finds the page number where a specific piece of text first appears."""
    snippet = " ".join(item_content.split()[:10])
    for page_num, page in enumerate(pdf_doc):
        if page.search_for(snippet):
            return page_num + 1
    return -1

def process_marking_scheme_document(pdf_path, diagram_out_dir, json_out_path):
    """Main function to process a marking scheme PDF."""
    if not os.path.exists(pdf_path):
        logging.error(f"Error: PDF file not found at {pdf_path}.")
        sys.exit(1)

    # Step 1: Extract all images to files and get their paths
    images_by_page = extract_images_from_pdf(pdf_path, diagram_out_dir)

    # Step 2: Extract text and parse into structured marking items
    logging.info("Extracting text and parsing marking scheme...")
    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    parsed_items = parse_marking_scheme_text(full_text)

    # Step 3: Associate images with each item and embed them as Base64
    logging.info("Associating and embedding diagrams...")
    for i, item in enumerate(parsed_items):
        item['diagrams'] = []
        page_num = find_item_page(doc, item['content'])

        start_page = page_num
        next_item_content = parsed_items[i+1]['content'] if i + 1 < len(parsed_items) else ""
        end_page = find_item_page(doc, next_item_content) if next_item_content else len(doc)
        if end_page != -1 and end_page < start_page: end_page = start_page

        page_range = range(start_page, end_page + 1) if end_page != -1 else ([start_page] if start_page != -1 else [])

        for p_num in page_range:
            if p_num in images_by_page:
                for image_path in images_by_page[p_num]:
                    encoded_image = encode_image_to_base64(image_path)
                    if encoded_image:
                        item['diagrams'].append(encoded_image)
        item['diagrams'] = sorted(list(set(item['diagrams'])))

    doc.close()

    # Step 4: Group items under their main question number
    final_output = {}
    for item in parsed_items:
        main_q_num_match = re.match(r"(0?\d+)", str(item['question_id']))
        if main_q_num_match:
            main_q_num = main_q_num_match.group(1).lstrip('0')
            if main_q_num not in final_output:
                final_output[main_q_num] = {"question_number": int(main_q_num), "parts": []}
            final_output[main_q_num]["parts"].append(item)

    # Step 5: Save the final data to the JSON file
    logging.info(f"Saving structured marking scheme to {json_out_path}...")
    with open(json_out_path, 'w', encoding='utf-8') as f:
        sorted_output = sorted(final_output.values(), key=lambda x: x['question_number'])
        json.dump(sorted_output, f, indent=4, ensure_ascii=False)

    logging.info(f"✓ Processing complete. JSON file contains embedded diagrams.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python process_markscheme.py <path_to_pdf> <diagrams_output_dir> <json_output_path>")
        sys.exit(1)

    pdf_file_path = sys.argv[1]
    diagram_output_dir = sys.argv[2]
    json_output_file = sys.argv[3]

    process_marking_scheme_document(pdf_file_path, diagram_output_dir, json_output_file)