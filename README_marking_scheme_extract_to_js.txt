Below is the complete self-contained script.
 It uses your original CONFIG block and the previous functions for text extraction and diagram cropping while replacing the two assignment functions with “smarter” versions that take vertical and horizontal proximity into account. 
 In the final JSON each mark‐scheme part (keyed by, e.g., “01”) now contains its text block plus only the diagrams/calculation images that are assigned as most spatially relevant.


### How It Works

1. **Text Extraction**  
   The function `collect_text_blocks()` uses the regular expression to capture each mark-scheme part’s header and body. It also uses `page.extract_words()` to capture the header’s bounding-box (x0, x1, y) for later spatial matching.

2. **Diagram Extraction**  
   `extract_page_images()` renders every PDF page as an image, crops each embedded image via its bounding box, saves the crop into the `DIAG_DIR`, and OCRs the image.

3. **Smart Assignment of Diagrams**  
   In `assign_diagrams_to_parts()`, for every diagram on a page the script computes a composite score using:
   - Vertical gap (dy) between the diagram’s top and the part’s header y-coordinate (with a weight).  
   - A horizontal penalty (with weight) when the diagram’s horizontal span does not overlap with the header’s span.  
   
   Each diagram is linked to the part with the lowest score.

4. **Final JSON Output**  
   The enriched blocks are then grouped into a dictionary keyed by the main question number (e.g., “01”), and saved to JSON.

Feel free to tweak `y_weight` and `x_weight` in the `assign_diagrams_to_parts()` function to better suit the layout of your documents. This code now also “uses bounding-box overlap or horizontal proximity” for ultra-precise matching.

Your merged JSON is now ready to be passed into further steps, such as training your hybrid BERT + CNN model.