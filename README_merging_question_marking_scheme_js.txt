Below is the full‐code merge pipeline updated to use a “smarter” diagram‐to‐question matcher. In this version, the code attempts an ultra‑precise assignment if the diagram dictionaries carry a bounding-box (via a key `"bbox"`) and if the extracted question blocks also include positional data (keys `"y"`, `"x0"`, and `"x1"`). Otherwise, it falls back to a proportional assignment.

Simply replace your old `assign_diagrams()` function in your merge pipeline with the updated version below (and leave the rest of the code unchanged).

Below is the entire merge pipeline


"""
MERGE PIPELINE
==============
Input
-----
1.  Question–paper text            ->  extracted_texts/sample.txt
2.  Diagram OCR + metadata         ->  extracted_diagrams/sample_ocr.txt
3.  Folder with diagram images     ->  extracted_diagrams/sample/
4.  Mark–scheme JSON (built by the
    marking scheme extraction script) -> extracted_marking_scheme.json

Output
------
merged_data.json      one self-contained file where every question holds:
                          • text
                          • matched diagram list
                          • marking-scheme list
"""



### Explanation

1. **Loaders:**  
   The functions `load_text()`, `load_marking_scheme()`, and `parse_ocr_file()` read in your question paper text, marking scheme JSON, and diagram OCR output.

2. **Grouping Diagrams:**  
   `group_diagrams_by_page()` groups diagram dictionaries by a three‑digit page number (e.g. "001").

3. **Question Extraction:**  
   `extract_questions()` splits each page into question blocks using a regular expression (looking for lines that start with “0 1 .”).

4. **Ultra‑Precise Matching:**  
   The updated `assign_diagrams()` function attempts to use bounding-box information (if available) to compute a composite score (vertical gap plus horizontal penalty). If the advanced positioning details are missing, it falls back to a simple proportional assignment.

5. **Merge Routine:**  
   In `merge_data()`, the code first merges continuation pages, then for each page splits into questions, assigns diagrams (via the smart matcher), and finally attaches the marking scheme from the JSON file (lookup by a two‑digit question key).

This final merged JSON (written to `merged_data.json`) will now have every question record containing its text, its assigned list of diagram dictionaries (with image file, OCR text, and bounding box if available), and the marking scheme details—all ready for your hybrid model training.

Feel free to adjust the weights `y_weight` and `x_weight` inside `assign_diagrams()` if needed.

Here’s a drop-in fix for  plus the full merge‐pipeline code. The new parser uses a regex to split on lines that look like

and captures everything until the next such header (or EOF). That eliminates the “not enough values to unpack” error and is robust to blank lines or missing colons elsewhere.

What changed?

 parse_ocr_file now uses a regex block‐split to reliably capture only those blocks beginning with page_...png .
 If your OCR file has lines that don’t match that header pattern (or stray blank lines), they’re simply ignored.
Everything else stays exactly the same, and your final  will be produced without the unpacking errors.