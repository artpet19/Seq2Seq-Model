# Seq2Seq-Model
Here is a comprehensive and complete **`README.md`** for your GitHub repository, combining both the **Data Processing Pipeline** and the **Seq2Seq Model Training System** into a single cohesive project workflow.

---

# Multimodal Exam Processing & Marking Scheme Generator 

An end-to-end multimodal machine learning system that converts raw exam **Question Papers (QP)** and **Marking Schemes (MS)** into structured datasets, and trains a **Seq2Seq neural model** (BERT + ResNet + GRU) to automatically generate marking schemes and answers from multimodal exam inputs (text + images/diagrams).

---

## Features

* **Automated Document Matching:** Scans and pairs corresponding Question Paper and Marking Scheme PDFs automatically.
* **Multimodal Feature Extraction:**
* Text extraction and layout parsing via `pdfplumber`.
* Diagram extraction and OCR captioning via Tesseract (`pytesseract`).


* **End-to-End Data Pipeline:** Transforms raw PDFs into clean, aligned JSON formats, then cleans and splits them into Train, Validation, and Test sets.
* **Hybrid Neural Architecture:**
* **Text Encoder:** Pretrained `BERT` (`bert-base-uncased`) for text representation.
* **Image Encoder:** Pretrained `ResNet-50` for visual feature extraction.
* **Decoder:** Recurrent `GRU` network with Teacher Forcing support for target sequence generation.



---

## System Architecture & Workflow

The project consists of two major components: **Data Preparation** and **Model Training**.

```text
[Raw PDF Files (QP & MS)]
           │
           ▼
Stage 1: QA Pair Matching (QA_Match_Picker.py)
           │
           ▼
Stage 2: Parsing & Multimodal Extraction (OCR + Layout Analysis)
           │
           ▼
Stage 3: JSON Restructuring & Normalization
           │
           ▼
Stage 4: Dataset Cleanup & Standardization
           │
           ▼
Stage 5: Split Dataset (Train / Validation / Test)
           │
           ▼
[Seq2Seq Multimodal Training (BERT + ResNet-50 + GRU)]
           │
           ▼
[Trained Model Weights (seq2seq_exam_model.pth)]

```

---

## Repository & Workspace Layout

The pipeline operates on the following directory structure:

```text
/content/drive/MyDrive/Code_Snippet/
├── Data Sets/                          # Raw input PDF files (QP and MS)
├── Out_put/                            # Matched QP-MS subdirectories
├── Ready_dataset/                      # Extracted raw question-marking JSON pairs
├── Ready_Dataset_Transformed_Output/   # Normalized and restructured JSON files
├── Model_Ready_Dataset/                # Unified multimodal records
├── Split_Dataset/                      # Partitioned output datasets
│   ├── train/                          # Training dataset JSONs
│   ├── validation/                     # Validation dataset JSONs
│   ├── test/                           # Test dataset JSONs
│   └── test_labels/                    # Ground truth labels for test set evaluation
└── seq2seq_exam_model.pth              # Saved PyTorch model checkpoint

```

---

## Prerequisites & Installation

### System Dependencies

* **Python 3.8+**
* **Tesseract OCR Engine** (for diagram captioning and text extraction)

#### Linux / Google Colab Setup

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr

```

### Python Dependencies

Install all required libraries via `pip`:

```bash
pip install torch torchvision transformers pdfplumber pdf2image pillow pytesseract numpy

```

---

## Execution Guide

### 1. Running in Google Colab

1. Open `FullPipeline.ipynb` in Google Colab.
2. Mount your Google Drive:
```python
from google.colab import drive
drive.mount('/content/drive')

```


3. Run the notebook sequentially. The pipeline will:
* Install system dependencies (`tesseract-ocr`).
* Run Stages 1 through 5 of the dataset creation pipeline.
* Load the generated dataset split into PyTorch DataLoaders.
* Train the Seq2Seq model over specified epochs and save `seq2seq_exam_model.pth`.



---

## Model Details

| Component | Architecture / Model | Function |
| --- | --- | --- |
| **Text Encoder** | `BERT` (`bert-base-uncased`) | Extracts 768-dimensional textual embedding from input questions |
| **Visual Encoder** | `ResNet-50` (Pretrained) | Extracts 2048-dimensional features from diagrams/images |
| **Feature Fusion** | Vector Concatenation | Combines text & image features into a 2816-dimensional hidden vector |
| **Decoder** | Single-layer `GRU` | Generates marking scheme token sequences step-by-step |
| **Loss Function** | CrossEntropyLoss | Ignores padding tokens (`tokenizer.pad_token_id`) |
| **Optimizer** | Adam | Learning rate: `0.001` |

---

## Logging & Output Files

* **`pipeline.log` / `comprehensive_pipeline.log**`: Tracks execution progress, warnings, and errors across both data extraction and model training.
* **`seq2seq_exam_model.pth`**: Saved PyTorch state dictionary containing model weights after training.

---

