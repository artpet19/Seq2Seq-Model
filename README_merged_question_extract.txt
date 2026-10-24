How This Updated Code Works
Below is a code that uses extra diagram metadata (including the diagram’s top coordinate from the PDF) to heuristically assign diagrams to the corresponding question on that page. 
In this example, we assume that your OCR extraction now produces extra metadata for each diagram (for example, via the updated extraction code shown previously). 
That metadata includes at least:

Then the code uses a matching function that sorts the diagrams (using their “top” coordinate) and splits them (in order) among the questions from that page. 
(If there is only one question on a page, all diagrams are assigned to it. 
Otherwise, the diagrams are partitioned by order, assigning roughly an equal number to each question.)

Below is the complete code:
    Loading & Grouping:
The code loads the full extracted text (pages marked with a page-break token) and diagram OCR results. 
The  function now groups diagrams by page using the extra metadata (particularly the ).
    Merging Pages:
If a page doesn’t start with a new question header (i.e. “0 1 .”), 
it is merged into the previous page—this covers multi–page questions.
    Extracting Questions:
The  function uses regex (tuned for your numbering scheme) to extract question blocks from the merged text.
    Matching Diagrams:
The new function  sorts the diagrams by their vertical (top) coordinate and then partitions them among the questions (using a proportional index assignment). 
Each question in the page then receives a “diagrams” key containing a list of the diagram metadata that likely belongs to it.
    Output JSON:
The JSON file groups data per page, and for each question on that page you have the question text, number, and its