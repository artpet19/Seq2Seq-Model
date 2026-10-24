# Pre-train the BERT Model
from transformers import BertTokenizer, BertForSequenceClassification

tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model_bert = BertForSequenceClassification.from_pretrained("bert-base-uncased")

# Tokenize text data
inputs = tokenizer(["Example question"], return_tensors="pt")
outputs = model_bert(**inputs)

# Train the CNN Model for Diagram
import torchvision.models as models
import torch.nn as nn

cnn_model = models.resnet50(pretrained=True)
cnn_model.fc = nn.Linear(2048, 512)  # Adjust final layer for embedding output

# Train the Hybrid Model
# Combine BERT outputs with CNN outputs using a fusion layer.
# Use Adam optimizer and Cross-Entropy loss for training

import torch
import torch.nn as nn

class HybridModel(nn.Module):
    def __init__(self, bert_model, cnn_model):
        super(HybridModel, self).__init__()
        self.bert = bert_model
        self.cnn = cnn_model
        self.fc = nn.Linear(1024, 512)  # Fusion Layer
    
    def forward(self, text_input, image_input):
        text_feat = self.bert(text_input)[0][:, 0, :]
        image_feat = self.cnn(image_input)
        combined = torch.cat((text_feat, image_feat), dim=1)
        return self.fc(combined)

hybrid_model = HybridModel(model_bert, cnn_model)
