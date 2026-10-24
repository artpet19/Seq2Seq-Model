import re
import json
import fitz  # PyMuPDF

pdf_path = "Data Sets/AQA-8464B1F-MS-JUN23.pdf"
json_out_path = "extracted_marking_scheme.json"

# Extract all text from the PDF
doc = fitz.open(pdf_path)
full_text = "".join(page.get_text() for page in doc)

# Regex patterns
QUESTION_HEADER_RE = re.compile(r"^Question\s+(\d+)", re.MULTILINE)
PART_RE = re.compile(
    r"^(\d{2}\.\d)\s+(.*?)(?=^\d{2}\.\d|^Question\s+\d+|\Z)",
    re.DOTALL | re.MULTILINE
)

# Find all question headers and their positions
question_headers = [(m.group(1), m.start()) for m in QUESTION_HEADER_RE.finditer(full_text)]
question_headers.append(("END", len(full_text)))  # Sentinel

# Extract structured data
structured_data = {}

for i in range(len(question_headers) - 1):
    q_number, start_pos = question_headers[i]
    _, end_pos = question_headers[i + 1]
    question_block = full_text[start_pos:end_pos]

    parts = []
    for match in PART_RE.finditer(question_block):
        part_number = match.group(1)
        body = match.group(2).strip()
        parts.append({"part": part_number, "body": body})

    structured_data[f"Question {q_number}"] = parts

# Save to JSON
with open(json_out_path, "w", encoding="utf-8") as f:
    json.dump(structured_data, f, indent=2, ensure_ascii=False)

print(f"✓ Structured marking scheme saved to {json_out_path}")
