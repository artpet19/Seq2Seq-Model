# -*- coding: utf-8 -*-
"""
Processes a PDF exam paper to extract questions and embed their associated
diagrams/images as Base64 strings directly within a JSON file.

Usage:
    python process_exam_with_embedded_images.py <path_to_pdf> <diagrams_output_dir> <json_output_path>

Example:
    python process_exam_with_embedded_images.py AQA-84654H-QP-JUN23.pdf ./diagrams_output aqa_exam.json
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
    """
    Reads an image file from disk and returns its Base64 encoded string.
    The string is safe to embed in a JSON file.
    """
    try:
        with open(image_path, "rb") as image_file:
            # Read the binary data and encode it
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except IOError as e:
        logging.error(f"Could not read image file for encoding {image_path}: {e}")
        return None

def extract_images_from_pdf(pdf_path, output_dir):
    """
    Extracts all images from a PDF, saves them to the specified directory,
    and returns a dictionary mapping page numbers to a list of image file paths.
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

                if pix.n - pix.alpha >= 4:
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
    """Removes extra whitespace and consolidates line breaks from text."""
    return ' '.join(text.strip().split())

def parse_questions_from_text(full_text):
    """
    Parses the full text of a PDF to identify questions and their content using robust regex.
    """
    question_pattern = re.compile(
        r"^\s*(?P<main>\d+)\s*(?:\((?P<part_a>\w+)\))?(?:\s*\((?P<part_b>[\w\d]+)\))?|"
        r"^\s*(?P<aqa_id>0\d)\s*\.\s*(?P<aqa_sub>\d)"
    )
    sub_part_pattern = re.compile(r"^\s*\(([\w\d]+)\)")

    lines = full_text.split('\n')
    questions = []
    current_question = None
    last_main_question_num = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        match = question_pattern.match(line_stripped)

        if match:
            if current_question:
                current_question['text'] = clean_text(current_question['text'])
                questions.append(current_question)

            q_id = ""
            if match.group('main'):
                main_num = match.group('main')
                part_a = match.group('part_a')
                part_b = match.group('part_b')
                q_id_parts = [p for p in [main_num, part_a, part_b] if p]
                q_id = ".".join(q_id_parts)
                last_main_question_num = main_num
            elif match.group('aqa_id'):
                main_num, sub_num = match.group('aqa_id'), match.group('aqa_sub')
                q_id = f"{main_num}.{sub_num}"
                last_main_question_num = main_num

            current_question = {"question_id": q_id, "text": line_stripped}
        elif sub_part_pattern.match(line_stripped) and last_main_question_num:
            if current_question:
                current_question['text'] = clean_text(current_question['text'])
                questions.append(current_question)

            sub_part_id = sub_part_pattern.match(line_stripped).group(1)
            q_id = f"{last_main_question_num}.{sub_part_id}"
            current_question = {"question_id": q_id, "text": line_stripped}
        elif current_question:
            current_question['text'] += " " + line

    if current_question:
        current_question['text'] = clean_text(current_question['text'])
        questions.append(current_question)

    return questions

def find_question_page(pdf_doc, question_text):
    """
    Finds the page number where a specific question's text first appears.
    """
    snippet = " ".join(question_text.split()[:15])
    for page_num, page in enumerate(pdf_doc):
        if page.search_for(snippet):
            return page_num + 1
    return -1

def process_question_paper(pdf_path, diagram_out_dir, json_out_path):
    """
    Main function to orchestrate the processing of a PDF exam paper.
    """
    if not os.path.exists(pdf_path):
        logging.error(f"Error: PDF file not found at {pdf_path}.")
        sys.exit(1)

    # Step 1: Extract images to files and get their paths
    images_by_page = extract_images_from_pdf(pdf_path, diagram_out_dir)

    # Step 2: Extract all text and parse into question structures
    logging.info("Extracting all text and structuring questions...")
    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    structured_questions = parse_questions_from_text(full_text)

    # Step 3: Associate images and embed them as Base64 strings
    logging.info("Embedding diagrams into question data...")
    for i, question in enumerate(structured_questions):
        question['diagrams'] = []
        page_num = find_question_page(doc, question['text'])
        
        start_page = page_num
        end_page = find_question_page(doc, structured_questions[i+1]['text']) if i + 1 < len(structured_questions) else len(doc)
        if end_page != -1 and end_page < start_page: end_page = start_page

        page_range = range(start_page, end_page + 1) if end_page != -1 else ([start_page] if start_page != -1 else [])
        
        for p_num in page_range:
            if p_num in images_by_page:
                for image_path in images_by_page[p_num]:
                    # Encode the image and add the string to the list
                    encoded_image_string = encode_image_to_base64(image_path)
                    if encoded_image_string:
                        question['diagrams'].append(encoded_image_string)
        
        question['diagrams'] = sorted(list(set(question['diagrams'])))

    doc.close()

    # Step 4: Group question parts under their main question number
    final_output = {}
    for q in structured_questions:
        main_q_num_match = re.match(r"(0?\d+)", q['question_id'])
        if main_q_num_match:
            main_q_num = main_q_num_match.group(1).lstrip('0')
            if main_q_num not in final_output:
                final_output[main_q_num] = {
                    "question_number": int(main_q_num),
                    "parts": []
                }
            final_output[main_q_num]["parts"].append(q)

    # Step 5: Save the final data to the JSON file
    logging.info(f"Saving processed data with embedded images to {json_out_path}...")
    with open(json_out_path, 'w', encoding='utf-8') as f:
        sorted_output = sorted(final_output.values(), key=lambda x: x['question_number'])
        json.dump(sorted_output, f, indent=4, ensure_ascii=False)

    logging.info(f"✓ Processing complete. Note: The JSON file size is larger due to embedded images.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python process_exam_with_embedded_images.py <path_to_pdf> <diagrams_output_dir> <json_output_path>")
        sys.exit(1)

    pdf_file_path = sys.argv[1]
    diagram_output_dir = sys.argv[2]
    json_output_file = sys.argv[3]

    process_question_paper(pdf_file_path, diagram_output_dir, json_output_file)