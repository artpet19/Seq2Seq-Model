# Dataset structure
# CSV or JSON format
[
    {
        "question_id": "Q1",
        "question_text": "What is the gradient of the given graph?",
        "diagram_path": "graphs/graph_1.png",
        "marking_scheme": "The gradient is calculated as rise/run. In this case, 3/2.",
        "metadata": {"subject": "Math", "topic": "Graph Analysis", "difficulty": "Medium"}
    },
    {
        "question_id": "Q2",
        "question_text": "Describe the trend in the plotted data.",
        "diagram_path": "graphs/graph_2.png",
        "marking_scheme": "The graph shows an increasing trend, meaning the values rise over time.",
        "metadata": {"subject": "Science", "topic": "Data Interpretation", "difficulty": "Easy"}
    }
]

# Preprocessing the Data
# For text-based data: ✅ Clean text – Remove unnecessary symbols, extra spaces, and special characters.
# ✅ Tokenize text – Convert sentences into tokens for NLP models using 

from transformers import BertTokenizer

tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
text = "What is the gradient of the given graph?"
tokens = tokenizer(text, return_tensors="pt")

# For image-based data: ✅ Standardize image size – Ensure all diagrams are resized to a consistent format (e.g., 224x224).
# ✅ Convert images to tensor format – Normalize pixel values for CNN training.

from PIL import Image
import torchvision.transforms as transforms

image = Image.open("graphs/graph_1.png")
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])
image_tensor = transform(image)

# Data Storage & Loading
# ✅ Use Pandas or JSON for easy access
# ✅ Batch loading – When training, load images & text together using PyTorch’s DataLoader

import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader

# Load dataset
df = pd.read_json("dataset.json")

# Custom dataset loader
class QuestionDataset(Dataset):
    def __init__(self, dataframe):
        self.data = dataframe
    
    def __getitem__(self, idx):
        text = self.data.iloc[idx]["question_text"]
        image_path = self.data.iloc[idx]["diagram_path"]
        return text, image_path
    
    def __len__(self):
        return len(self.data)

dataset = QuestionDataset(df)
dataloader = DataLoader(dataset, batch_size=16, shuffle=True)



