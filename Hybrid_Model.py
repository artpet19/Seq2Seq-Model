from transformers import BertModel, BertTokenizer
import torch
import torchvision.models as models
import torch.nn as nn

# Load BERT model for text processing
bert_model = BertModel.from_pretrained("bert-base-uncased")
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

# Load CNN model for diagram processing
cnn_model = models.resnet50(pretrained=True)

# Define Fusion Layer (concatenation)
class HybridModel(nn.Module):
    def __init__(self, bert_model, cnn_model):
        super(HybridModel, self).__init__()
        self.bert = bert_model
        self.cnn = cnn_model
        self.fc = nn.Linear(1024, 512)  # Adjust layer sizes as needed
    
    def forward(self, text_input, image_input):
        text_feat = self.bert(text_input)[0][:, 0, :]  # Extract features from BERT
        image_feat = self.cnn(image_input)  # Extract features from CNN
        combined = torch.cat((text_feat, image_feat), dim=1)
        return self.fc(combined)

# Instantiate the hybrid model
hybrid_model = HybridModel(bert_model, cnn_model)
