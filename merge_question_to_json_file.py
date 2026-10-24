import re
import os
import json

def load_extracted_text(text_file):
    """
    Loads the extracted text file.
    Assumes pages are separated by the marker:
       "\n\n---PAGE BREAK---\n\n"
    """
    with open(text_file, 'r', encoding='utf8') as f:
        return f.read()

def load_ocr_results(ocr_file):
    """
    Loads the OCR results file and returns a dictionary mapping image file names
    to diagram metadata. Expected format for each entry is:

      page_001_img_01.png:
        OCR_TEXT: <ocr text extracted>
        PDF_BBOX: x0,top,x1,bottom

    (Each entry is separated by a blank line.)

    For simplicity, this parser expects the PDF_BBOX values to be comma-delimited.
    """
    ocr_data = {}
    with open(ocr_file, 'r', encoding='utf8') as f:
        content = f.read().strip()
    entries = content.split("\n\n")
    for entry in entries:
        if not entry.strip():
            continue
        # Split the header line (filename) from the rest
        parts = entry.split(":\n", 1)
        if len(parts) != 2:
            continue
        image_name = parts[0].strip()
        # Initialize metadata dictionary.
        data = {}
        for line in parts[1].splitlines():
            line = line.strip()
            if line.startswith("OCR Text"):
                # Expected format: OCR Text   : <text>
                _, value = line.split(":", 1)
                data["ocr_text"] = value.strip()
            elif line.startswith("PDF BBox"):
                # Expected format: PDF BBox   : (x0, top, x1, bottom)
                _, value = line.split(":", 1)
                # Remove any parentheses and spaces, then split by comma.
                value = value.strip().replace("(", "").replace(")", "")
                try:
                    bbox = tuple(float(v.strip()) for v in value.split(","))
                    data["pdf_bbox"] = bbox
                except Exception:
                    data["pdf_bbox"] = (0, 0, 0, 0)
            # You can add further keys (like pixel_bbox) if available.
        ocr_data[image_name] = data
    return ocr_data

def group_diagrams_by_page(ocr_data, diagram_dir):
    """
    Groups diagram OCR results by page number using the naming convention
    "page_XXX_img_YY.png". The data for each diagram includes image_file,
    ocr_text, and pdf_bbox.
    
    Returns a dict:
      { "001": [ { "image_file": ..., "ocr_text": ..., "pdf_bbox": (...) }, ... ], ... }
    """
    page_diagrams = {}
    for image_name, meta in ocr_data.items():
        m = re.search(r'page_(\d+)_img_', image_name)
        if m:
            page_num = m.group(1)  # e.g., "001"
            entry = {
                "image_file": os.path.join(diagram_dir, image_name),
                "ocr_text": meta.get("ocr_text", ""),
                "pdf_bbox": meta.get("pdf_bbox", (0, 0, 0, 0))
            }
            page_diagrams.setdefault(page_num, []).append(entry)
    return page_diagrams

def extract_questions_from_page(page_text):
    """
    Extracts questions from page text based on your numbering format.
    It expects each question to begin with a header line of the form:
       "0 1 . <number> <question text>"
    
    The regex is multiline and uses DOTALL so that text is captured until
    the next header or end-of-page.
    
    Returns a list of questions:
         { "question_number": <number>, "text": <full question text> }
    """
    pattern = r'(?m)^0\s*1\s*\.\s*(\d+)\s+(.*?)(?=^0\s*1\s*\.\s*\d+\s+|\Z)'
    matches = list(re.finditer(pattern, page_text, flags=re.DOTALL))
    questions = []
    for m in matches:
        q_number = m.group(1).strip()
        q_text = m.group(2).strip()
        questions.append({
            "question_number": q_number,
            "text": q_text
        })
    return questions

def match_diagrams_to_questions(diagrams, questions):
    """
    Given a list of diagram dicts from a page (each containing at least a 'pdf_bbox')
    and the list of extracted questions (in order of appearance), assign diagrams
    to specific questions using a simple ordering heuristic.
    
    We sort the diagrams by their top coordinate (from pdf_bbox) and then assign
    them proportionally. For example, if there is only one question, then all diagrams
    are assigned to it.
    
    Returns a dictionary mapping a question index to a list of diagrams.
    """
    # In case no diagrams are provided, return empty assignment.
    if not diagrams:
        return {i: [] for i in range(len(questions))}
        
    # Sort diagrams by the top coordinate (pdf_bbox[1])
    diagrams_sorted = sorted(diagrams, key=lambda d: d.get("pdf_bbox", (0,0,0,0))[1])
    num_questions = len(questions)
    assigned = {i: [] for i in range(num_questions)}
    
    # Heuristic: assign diagram i to question index = min(int(i * num_questions / total_diagrams), num_questions-1)
    total = len(diagrams_sorted)
    for idx, diag in enumerate(diagrams_sorted):
        q_idx = min(int(idx * num_questions / total), num_questions - 1)
        assigned[q_idx].append(diag)
    return assigned

def merge_extracted_data(text_file, ocr_file, diagram_dir, output_json):
    """
    Merges the question text and diagram OCR data into a JSON structure.
    
    Process:
      1. Load extracted text (pages separated by "\n\n---PAGE BREAK---\n\n").
      2. Load diagram OCR results and group them by page.
      3. For pages that do not begin with a new question header ("0 1 ."),
         assume continuation of the previous page and merge.
      4. For each merged page, extract questions and then assign diagrams to
         specific questions using the match_diagrams_to_questions() heuristic.
    
    The resulting JSON contains a list of pages, each with:
      - "page_number"
      - "full_text": complete merged text
      - "questions": a list of dicts with:
          "question_number", "text", and "diagrams" (a list of diagram dicts).
    """
    full_text = load_extracted_text(text_file)
    ocr_data = load_ocr_results(ocr_file)
    page_diagrams = group_diagrams_by_page(ocr_data, diagram_dir)
    
    # Split the full text into pages.
    pages = full_text.split("\n\n---PAGE BREAK---\n\n")
    merged_pages = []  # Each entry: { page_number, full_text, diagrams }
    
    for i, page_text in enumerate(pages):
        page_num = str(i + 1).zfill(3)
        text_strip = page_text.lstrip()
        if i > 0 and not text_strip.startswith("0 1 ."):
            # If a page does not start with a new question header,
            # assume its content is a continuation of the previous page.
            if merged_pages:
                merged_pages[-1]["full_text"] += "\n" + page_text
                merged_pages[-1]["diagrams"] += page_diagrams.get(page_num, [])
            else:
                merged_pages.append({
                    "page_number": page_num,
                    "full_text": page_text,
                    "diagrams": page_diagrams.get(page_num, [])
                })
        else:
            merged_pages.append({
                "page_number": page_num,
                "full_text": page_text,
                "diagrams": page_diagrams.get(page_num, [])
            })
    
    # Build final merged data structure.
    extracted_question_to_js = {"pages": []}
    for page in merged_pages:
        questions = extract_questions_from_page(page["full_text"])
        # Use our matching function to assign diagrams to specific questions.
        diag_assignment = match_diagrams_to_questions(page["diagrams"], questions)
        # Add the assigned diagrams to each question.
        for idx, q in enumerate(questions):
            q["diagrams"] = diag_assignment.get(idx, [])
        extracted_question_to_js["pages"].append({
            "page_number": page["page_number"],
            "full_text": page["full_text"],
            "questions": questions
        })
    
    with open(output_json, "w", encoding="utf8") as f:
        json.dump(extracted_question_to_js, f, indent=4)
    
    print(f"Merged extracted data saved to {output_json}")

if __name__ == "__main__":
    # Update paths to match your environment.
    TEXT_FILE = "extracted_texts/sample.txt"
    OCR_FILE = "extracted_diagrams/sample_ocr.txt"
    DIAGRAM_DIR = "extracted_diagrams/sample"  # Directory where diagram images are stored.
    OUTPUT_JSON = "extracted_question_to_js.json"

    merge_extracted_data(TEXT_FILE, OCR_FILE, DIAGRAM_DIR, OUTPUT_JSON)