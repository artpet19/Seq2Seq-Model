# ---------- CONFIG ---------- #
PDF_QN_PATH   = r"Out_put/Match_008_AQA-8464B2F-JUN23/AQA-8464B2F-QP-JUN23.pdf"   # <- source PDF
RAW_TXT_PATH  = r"extracted_question_to_text.txt"       # optional text dump
JSON_OUT_PATH = r"extracted_question_to_js.json"          # structured output
DIAG_DIR      = r"extracted_diagrams"                            # folder to save diagram crops
DPI           = 300                                      # render resolution
# ---------------------------- #

import os, re, json, pdfplumber
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from math import hypot

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ───────────────────────── Utilities ─────────────────────────
def _dist(c1, c2):
    """Euclidean distance between two 2D points."""
    return hypot(c1[0] - c2[0], c1[1] - c2[1])

def _overlap_1d(a0, a1, b0, b1):
    """Return positive overlap length in 1D; otherwise 0."""
    return max(0, min(a1, b1) - max(a0, b0))

# ───────────────────────── TEXT EXTRACTION ─────────────────────────
# RegEx for mark-scheme part headers like "01.1"

PART_RE = re.compile(
    r"(?m)^\s*(?P<id>\d{1,2}\.\d+)\s+(?P<body>.*?)(?=^\s*\d{1,2}\.\d+\s+|\Z)",
    re.DOTALL,
)

def dump_pdf_to_txt(pdf_path: str, txt_out: str) -> None:
    """Dump every page’s text (with page-break markers) – useful for eyeballing."""
    with pdfplumber.open(pdf_path) as pdf, open(txt_out, "w", encoding="utf-8") as f:
        for p in pdf.pages:
            f.write(p.extract_text(x_tolerance=1) or "")
            f.write("\n\n---PAGE BREAK---\n\n")
    print(f"✓ Raw mark-scheme text dumped → {txt_out}")

def collect_text_blocks(pdf_path: str) -> list:
    """
    Returns a list of dictionaries, each with:
        - part: the question-number part ID (e.g. "01.2")
        - body: its text (detail, including marks, AO, explanatory notes, etc.)
        - page: PDF page number (1 based)
        - x0, x1, y: coordinates of the header’s bounding box (from the first matching word)
    """
    blocks = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg_num, page in enumerate(pdf.pages, start=1):
            txt = page.extract_text(x_tolerance=1) or ""
            for m in PART_RE.finditer(txt):
                part_id = m.group("id").strip()
                body = m.group("body").strip()
                # Locate header's position using the first word that starts with the part ID.
                header_words = [w for w in page.extract_words() if w["text"].startswith(part_id)]
                if header_words:
                    w0 = header_words[0]
                    x0, x1, y_top = w0["x0"], w0["x1"], w0["top"]
                else:
                    x0, x1, y_top = 0, 0, 1e6  # fallback
                blocks.append({
                    "part": part_id,
                    "body": body,
                    "page": pg_num,
                    "x0": x0,
                    "x1": x1,
                    "y": y_top
                })
    return blocks

# ───────────────────────── DIAGRAM EXTRACTION ─────────────────────────
def extract_page_images(pdf_path: str, out_dir: str, dpi=DPI) -> list:
    """
    Extracts every embedded diagram (or calculation image) from the PDF.
    Returns a list of dicts, each containing:
        - page: PDF page number (1 based)
        - file: saved image path
        - bbox: [x0, top, x1, bottom] (in PDF points)
        - ocr: text from Tesseract OCR on the cropped image
    """
    os.makedirs(out_dir, exist_ok=True)
    page_imgs = convert_from_path(pdf_path, dpi=dpi)
    diags = []
    with pdfplumber.open(pdf_path) as pdf:
        for idx, (pl_page, pil_page) in enumerate(zip(pdf.pages, page_imgs)):
            pg_no = idx + 1
            for j, meta in enumerate(pl_page.images):
                x0, top, x1, bottom = meta["x0"], meta["top"], meta["x1"], meta["bottom"]
                s = dpi / 72  # Scale factor: PDF points to pixels
                crop = pil_page.crop((int(x0 * s), int(top * s), int(x1 * s), int(bottom * s)))
                fname = f"MS_p{pg_no:03}_img_{j+1:02}.png"
                fpath = os.path.join(out_dir, fname)
                crop.save(fpath)
                diags.append({
                    "page": pg_no,
                    "file": fpath,
                    "bbox": [x0, top, x1, bottom],
                    "ocr": pytesseract.image_to_string(crop, lang="eng").strip()
                })
    return diags

# ───────────────────────── Smart Diagram Assignment ─────────────────────────
def assign_diagrams_to_parts(blocks: list, diags: list, y_weight=1.0, x_weight=0.3) -> list:
    """
    For each diagram, assign it to the question number part that minimizes a composite score.
    The score is calculated as:
    
        score = vertical_gap * y_weight + horizontal_gap * x_weight
        
    Vertical gap (dy) is computed as max(0, diag_top - part_header_y). The horizontal penalty:
      - 0 if the header's horizontal span (x0 to x1) overlaps with the diagram's horizontal span.
      - Otherwise, the gap between the closest edges.
    """
    # Group parts and diagrams by page number.
    parts_by_page = {}
    for b in blocks:
        parts_by_page.setdefault(b["page"], []).append(b)
    diags_by_page = {}
    for d in diags:
        diags_by_page.setdefault(d["page"], []).append(d)

    # For each page, assign diagrams smartly.
    for pg, parts in parts_by_page.items():
        for p in parts:
            p.setdefault("diagrams", [])
        for dg in diags_by_page.get(pg, []):
            x0d, top_d, x1d, _ = dg["bbox"]
            best_part, best_score = None, 1e9
            for p in parts:
                # Vertical gap: if diagram appears above part header, treat gap as 0.
                dy = max(0, top_d - p["y"])
                # Horizontal penalty: check horizontal overlap.
                ov = _overlap_1d(x0d, x1d, p["x0"], p["x1"])
                if ov > 0:
                    dx_pen = 0
                else:
                    # If no overlap, compute horizontal gap.
                    if x1d < p["x0"]:
                        dx = p["x0"] - x1d
                    elif x0d > p["x1"]:
                        dx = x0d - p["x1"]
                    else:
                        dx = 0
                    dx_pen = dx * x_weight
                score = dy * y_weight + dx_pen
                if score < best_score:
                    best_score = score
                    best_part = p
            if best_part is not None:
                best_part["diagrams"].append(dg)

    # Ensure every block has a diagrams key.
    for b in blocks:
        b.setdefault("diagrams", [])
    return blocks

# ───────────────────────── Final Assembly ─────────────────────────
def build_mark_scheme():
    # 1. Dump raw text (optional)
    dump_pdf_to_txt(PDF_QN_PATH, RAW_TXT_PATH)

    # 2. Extract text blocks (with header positions)
    print("⋯ extracting text blocks …")
    text_blocks = collect_text_blocks(PDF_QN_PATH)

    # 3. Extract diagram images & OCR from the PDF
    print("⋯ extracting diagrams …")
    diagrams = extract_page_images(PDF_QN_PATH, DIAG_DIR)

    # 4. Smart assignment: attach each diagram to the relevant part using vertical & horizontal proximity.
    print("⋯ assigning diagrams to parts …")
    enriched_blocks = assign_diagrams_to_parts(text_blocks, diagrams)

    # 5. Group into final dict keyed by main question number (e.g., "01", "02", …)
    qn_dict = {}
    for blk in enriched_blocks:
        key = blk["part"].split(".")[0]
        qn_dict.setdefault(key, []).append(blk)

    # 6. Save final JSON
    out_dir = os.path.dirname(JSON_OUT_PATH)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(JSON_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(qn_dict, f, indent=2)
    print(f"✓ Questions JSON saved → {JSON_OUT_PATH} (questions: {len(qn_dict)})")

if __name__ == "__main__":
    build_mark_scheme()
