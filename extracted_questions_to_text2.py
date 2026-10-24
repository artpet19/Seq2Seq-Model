# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
import re
from PIL import Image
import pytesseract
import fitz  # PyMuPDF

# --- 1. SETUP LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Tesseract command location - make sure this is correct for your system
# You might need to adjust this path.
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# --- 2. HELPER FUNCTIONS ---

def extract_images(pdf_path, output_dir):
    """
    Extracts images from a PDF and saves them to a directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    images_info = []
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            image_filename = f"image_page_{i+1}_xref_{xref}.png"
            image_path = os.path.join(output_dir, image_filename)
            pix.save(image_path)
            images_info.append({"image_file": image_path, "page": i + 1})
    doc.close()
    return images_info

def extract_text(pdf_path):
    """
    Extracts text from a PDF.
    """
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        # Corrected method name: get_text() instead of getText()
        text += page.get_text()
    doc.close()
    return text

def find_questions_and_parts(text):
    """
    Identifies questions and their parts based on common patterns.
    """
    questions = {}
    current_question_number = None

    # This regex looks for patterns like "1.", "1 (a)", or "1(a)"
    # It correctly captures both the main question number and the part.
    question_pattern = re.compile(r'^\s*(\d+)\s*\((?:\s*([a-z]))\s*\)|^\s*(\d+)\s*\.')
    lines = text.split('\n')

    for i, line in enumerate(lines):
        match = question_pattern.match(line)
        if match:
            main_q = match.group(1) or match.group(3)
            part_q = match.group(2)
            
            if main_q:
                main_q = int(main_q)
                
                if main_q not in questions:
                    questions[main_q] = {"question_number": main_q, "parts": []}
                
                # Check for question parts
                if part_q:
                    full_q_id = f"{main_q}{part_q}"
                    questions[main_q]["parts"].append({
                        "question_id": full_q_id,
                        "text": line.strip()
                    })
                else:
                    # This is a full question without parts
                    questions[main_q]["parts"].append({
                        "question_id": str(main_q),
                        "text": line.strip()
                    })

    return questions

def process_question_paper(pdf_path, diagram_out_dir, json_out_path):
    """
    Main function to process a question paper PDF.
    """
    if not os.path.exists(pdf_path):
        logging.error(f"Error: PDF file not found at {pdf_path}.")
        sys.exit(1)
    
    # Extract text from the PDF
    logging.info("... extracting text from PDF...")
    full_text = extract_text(pdf_path)
    
    # Find and structure questions
    logging.info("... structuring questions from text...")
    structured_questions = find_questions_and_parts(full_text)

    # Extract diagrams and save them
    logging.info("... extracting and saving diagrams...")
    diagrams_info = extract_images(pdf_path, diagram_out_dir)
    
    # Merge diagrams into the questions data structure
    logging.info("... merging diagrams with questions...")
    for q_num, question_data in structured_questions.items():
        for part in question_data.get("parts", []):
            part["diagrams"] = []
            # Find diagrams that belong to this question part (this is a simplified approach)
            # A more robust solution would involve checking text proximity to images.
            for diagram in diagrams_info:
                if f"Fig. {q_num}" in full_text: # Simple heuristic
                    part["diagrams"].append(diagram)
    
    # Save the processed data to a JSON file
    logging.info(f"Saving processed data to {json_out_path}...")
    with open(json_out_path, 'w', encoding='utf-8') as f:
        json.dump(list(structured_questions.values()), f, indent=2, ensure_ascii=False)
    
    logging.info(f"✓ Processing complete. Output saved to {json_out_path}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python extracted_questions_to_text.py <path_to_pdf> <diagrams_output_dir> <json_output_path>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    diagram_out_dir = sys.argv[2]
    json_out_path = sys.argv[3]
    
    process_question_paper(pdf_path, diagram_out_dir, json_out_path)
    