
The code function so that each diagram’s saved data includes extra metadata (such as the page number and bounding box coordinates) that you can later use to match a diagram with its corresponding question. 
In this revised version, the dictionary returned by the diagram extractor will include not only the OCR’d text but also the page number and the original bounding box coordinates (both in PDF points and in pixel values). 
You can then use these details during your merging step to determine which diagram lies near—which part of—the extracted text.

Below stepwise function of  the code:

Below is one way to modify your code so that each diagram’s saved data includes extra metadata (such as the page number and bounding box coordinates) that you can later use to match a diagram with its corresponding question. In this revised version, the dictionary returned by the diagram extractor will include not only the OCR’d text but also the page number and the original bounding box coordinates (both in PDF points and in pixel values). You can then use these details during your merging step to determine which diagram lies near—which part of—the extracted text.



Here’s an end-to-end script that will:  
1) pull out all the raw text (via pdfplumber)  
2) render pages to images (via pdf2image)  
3) locate embedded diagrams in the PDF (via pdfplumber’s image metadata)  
4) crop those diagram‐regions out of the page images (via Pillow)  
5) run OCR on each crop (via Tesseract) to pull out any labels/captions  


Explanation of key steps  
- We use pdfplumber.open to get precise coordinates of every embedded image on each page.  
- pdf2image.convert_from_path gives us high-res PIL pages so crops look sharp.  
- Coordinates are in “points” (72 pt/in), so we scale by dpi/72 to get pixel values.  
- Each crop is Tesseract’d with pytesseract.image_to_string(…) to pull out any text in the diagram (labels, captions, axis titles, etc.).

What you can do next  
• Refine OCR accuracy by tuning Tesseract’s –psm (mode) or using image_to_data for bounding-box-level confidence.  
• Run a simple CV filter (edge detection + contour analysis) to drop non-diagram images or isolate charts.  
• Use NLP on extracted text + OCR output to auto-classify question types, tag diagrams by content, or generate metadata.  
• If your PDFs are purely scanned images, run an initial global OCR on the full page image first, then merge with the pdfplumber text.


1. **Extra Metadata Added:**  
   Each diagram’s entry now includes:
   - **`page_number`** – so you know on which page the diagram was found.
   - **`pdf_bbox`** – the original bounding box coordinates from the PDF.  
   - **`pixel_bbox`** – the corresponding pixel coordinates from the rendered page image.

2. **Matching Diagrams to Questions:**  
   By having the page number along with bounding box details:
   - You can later compare the diagram’s location with the text coordinates. For instance, if you extract the coordinates (or even just the vertical position) of each question header using pdfplumber’s layout information, you may heuristically match a diagram to the question that appears closest to its bounding box.
   - Alternatively, if your text extraction preserves elements (like “Figure 1”), you can develop a matching rule based on explicit identifiers.

3. **Flexibility for Later Processing:**  
   When combining data into a JSON file (or passing it to your hybrid model), you now have enough spatial information to devise a matching strategy between text blocks and diagram regions. For example, you might decide that a diagram “belongs” to the question whose text has the closest lower bound in vertical space relative to the diagram’s upper coordinate.

This additional data should give you the leverage required to design a matching algorithm tailored to your document layout. Feel free to ask if you’d like more ideas or code examples for associating the diagrams (using these coordinates) with specific question text excerpts!

