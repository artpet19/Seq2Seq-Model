import os
import json
import torch
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
import torch.optim as optim
from transformers import BertModel, BertTokenizer
import torchvision.models as models
from collections import defaultdict
import random

# Define the full Seq2Seq model with an encoder-decoder architecture
class Seq2SeqModel(nn.Module):
    """
    A sequence-to-sequence neural network for text generation.
    It uses a BERT encoder for text, a ResNet encoder for images, and a GRU decoder
    to generate the output sequence.
    """
    def __init__(self, num_classes, bert_model, cnn_model):
        super(Seq2SeqModel, self).__init__()
        # Encoders
        self.text_encoder = bert_model
        # Use a pretrained ResNet, but only the feature extraction part
        self.image_encoder = nn.Sequential(*list(cnn_model.children())[:-1])
        
        # Calculate the combined feature size
        # ResNet-50 has a flattened output of 2048 features, and BERT-base has 768.
        combined_feature_size = 2048 + 768
        
        # Decoder
        # The decoder takes the combined encoder output as its initial hidden state
        # The input to the decoder at each step is the previous generated token embedding
        self.decoder = nn.GRU(
            input_size=num_classes, # Input size for the decoder is the vocab size (one-hot)
            hidden_size=combined_feature_size,
            num_layers=1,
            batch_first=True
        )
        # Linear layer to project the decoder output to the size of our vocabulary
        self.output_layer = nn.Linear(combined_feature_size, num_classes)
        self.max_len = 128 # The max length of the output sequence
    
    def forward(self, text_input, image_input, target=None, teacher_forcing_ratio=0.5):
        # Pass the inputs through the encoders
        text_features = self.text_encoder(text_input).pooler_output
        image_features = self.image_encoder(image_input)
        image_features = torch.flatten(image_features, 1)

        # Combine the features
        combined_features = torch.cat((text_features, image_features), dim=1)
        
        batch_size = combined_features.size(0)
        
        if target is not None:
            # Training mode with teacher forcing
            target_length = target.size(1)
            decoder_outputs = torch.zeros(batch_size, target_length, self.output_layer.out_features).to(combined_features.device)
            
            # Initial decoder input is the [CLS] token (or start token, here we just use a zero vector)
            decoder_input = torch.zeros(batch_size, self.output_layer.out_features, device=combined_features.device)
            
            # Initial hidden state for the decoder is the encoder's combined output
            hidden = combined_features.unsqueeze(0)
            
            for t in range(target_length):
                decoder_input = decoder_input.unsqueeze(1)
                output, hidden = self.decoder(decoder_input, hidden)
                
                # Predict the next token
                prediction = self.output_layer(output.squeeze(1))
                decoder_outputs[:, t, :] = prediction
                
                # Teacher forcing: decide whether to use the target token or the model's own prediction
                teacher_force = random.random() < teacher_forcing_ratio
                if teacher_force:
                    # Use the true target token as the next input
                    next_token = torch.zeros(batch_size, self.output_layer.out_features, device=combined_features.device)
                    # We need to scatter the true token IDs into a one-hot vector
                    next_token.scatter_(1, target[:, t].unsqueeze(1), 1)
                    decoder_input = next_token
                else:
                    # Use the model's own prediction as the next input
                    top1 = prediction.argmax(1)
                    next_token = torch.zeros(batch_size, self.output_layer.out_features, device=combined_features.device)
                    next_token.scatter_(1, top1.unsqueeze(1), 1)
                    decoder_input = next_token
                    
            return decoder_outputs
        else:
            # Inference mode (simplified greedy search)
            outputs = []
            
            # Initial decoder input is a zero vector
            decoder_input = torch.zeros(1, self.output_layer.out_features, device=combined_features.device)
            
            # Initial hidden state for the decoder is the encoder's combined output
            hidden = combined_features.unsqueeze(0)
            
            for i in range(self.max_len):
                output, hidden = self.decoder(decoder_input.unsqueeze(1), hidden)
                prediction = self.output_layer(output.squeeze(1))
                
                # Get the token with the highest probability
                top1 = prediction.argmax(1)
                outputs.append(top1.squeeze().item())
                
                # Prepare the next decoder input
                decoder_input = torch.zeros(1, self.output_layer.out_features, device=combined_features.device)
                decoder_input[0, top1.item()] = 1
                
                # Stop if the model predicts the end-of-sequence token
                if top1.item() == 102: # BERT's [SEP] token
                    break
            
            return outputs
    
class Seq2SeqDataset(Dataset):
    """
    A custom PyTorch Dataset to load data from a directory of JSON files for Seq2Seq.
    """
    def __init__(self, data_dir, tokenizer, labels_dir=None):
        self.data = []
        self.tokenizer = tokenizer
        
        data_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.json')]
        
        # Load all data files and their labels
        if labels_dir:
            label_files = [os.path.join(labels_dir, f) for f in os.listdir(labels_dir) if f.endswith('.json')]
            label_map_file_names = {os.path.basename(f): f for f in label_files}
            
            for data_file in data_files:
                fname = os.path.basename(data_file)
                if fname in label_map_file_names:
                    label_file = label_map_file_names[fname]
                    
                    with open(data_file, "r", encoding="utf-8") as f:
                        data_list = json.load(f)
                    with open(label_file, "r", encoding="utf-8") as f:
                        labels_list = json.load(f)
                    
                    for entry_data, entry_label in zip(data_list, labels_list):
                        # The test labels file only contains the marking scheme body
                        label_body = entry_label.get("marking_scheme", {}).get("body", "")
                        if label_body:
                            entry_data["marking_scheme"] = {"body": label_body}
                            self.data.append(entry_data)
        else:
            for file_path in data_files:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                self.data.extend(file_data)
    
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        entry = self.data[idx]
        
        # Get pre-tokenized text data (input sequence)
        text_data = torch.tensor(entry.get("text", []), dtype=torch.long)
        
        # Get image data.
        image_data_list = entry.get("image", [])
        if image_data_list:
            image_data = torch.tensor(image_data_list, dtype=torch.float32)
        else:
            # Placeholder for a single 224x224 RGB image
            image_data = torch.zeros(3, 224, 224, dtype=torch.float32)

        # Get the label (target sequence) and tokenize it
        label_body = entry.get("marking_scheme", {}).get("body", "")
        # The tokenizer automatically handles padding and special tokens
        tokenized_label = self.tokenizer(
            label_body, 
            return_tensors="pt", 
            truncation=True, 
            padding=True
        ).input_ids.squeeze(0)
        
        return text_data, image_data, tokenized_label

def pad_sequence_custom(batch):
    """
    A custom collate function to pad sequences in a batch to the same length.
    Now handles two sequences: input text and target label.
    """
    text_inputs = [item[0] for item in batch]
    image_inputs = [item[1] for item in batch]
    labels = [item[2] for item in batch]
    
    # Pad all input text sequences to the same length
    max_len_text = max(len(s) for s in text_inputs)
    padded_text_inputs = torch.stack([
        torch.nn.functional.pad(s, (0, max_len_text - len(s)), 'constant', 0) 
        for s in text_inputs
    ])
    
    # Pad all label sequences to the same length
    max_len_labels = max(len(s) for s in labels)
    padded_labels = torch.stack([
        torch.nn.functional.pad(s, (0, max_len_labels - len(s)), 'constant', 0)
        for s in labels
    ])
    
    # Stack images
    stacked_image_inputs = torch.stack(image_inputs)
    
    return padded_text_inputs, stacked_image_inputs, padded_labels

def train_model(model, train_loader, val_loader, criterion, optimizer, num_epochs, device):
    """
    Trains and validates the Seq2Seq model.
    """
    model.train()  # Set the model to training mode
    
    for epoch in range(num_epochs):
        running_loss = 0.0
        
        # Training loop
        for i, (text_inputs, image_inputs, labels) in enumerate(train_loader):
            text_inputs = text_inputs.to(device)
            image_inputs = image_inputs.to(device)
            labels = labels.to(device)
            
            optimizer.zero_grad()
            
            # Forward pass
            outputs = model(text_inputs, image_inputs, labels)
            
            # Reshape outputs to (N, C) and labels to (N) for CrossEntropyLoss
            loss = criterion(outputs.view(-1, outputs.size(-1)), labels.view(-1))
            
            # Backward pass and optimization
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
            if (i+1) % 10 == 0:  # Print every 10 mini-batches
                print(f"Epoch [{epoch+1}/{num_epochs}], Batch [{i+1}/{len(train_loader)}], Loss: {loss.item():.4f}")
        
        epoch_loss = running_loss / len(train_loader)
        print(f"Epoch {epoch+1} Training Loss: {epoch_loss:.4f}")
        
        # Validation loop
        model.eval()  # Set the model to evaluation mode
        val_loss = 0.0
        
        with torch.no_grad():
            for text_inputs, image_inputs, labels in val_loader:
                text_inputs = text_inputs.to(device)
                image_inputs = image_inputs.to(device)
                labels = labels.to(device)
                
                outputs = model(text_inputs, image_inputs, labels)
                loss = criterion(outputs.view(-1, outputs.size(-1)), labels.view(-1))
                val_loss += loss.item()
        
        val_epoch_loss = val_loss / len(val_loader)
        print(f"Epoch {epoch+1} Validation Loss: {val_epoch_loss:.4f}")
        
        model.train() # Set the model back to training mode for the next epoch

if __name__ == "__main__":
    # Define constants for the new directory structure.
    DATASET_ROOT = "Split_Datasets"
    TRAIN_DATA_DIR = os.path.join(DATASET_ROOT, "train")
    VAL_DATA_DIR = os.path.join(DATASET_ROOT, "validation")
    TEST_DATA_DIR = os.path.join(DATASET_ROOT, "test")
    TEST_LABELS_DIR = os.path.join(DATASET_ROOT, "test_labels")
    
    NUM_EPOCHS = 5
    BATCH_SIZE = 32
    LEARNING_RATE = 0.001
    
    # Check for GPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Initialize tokenizer for both input and output sequences
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    
    # Load data for training and validation.
    train_dataset = Seq2SeqDataset(TRAIN_DATA_DIR, tokenizer)
    val_dataset = Seq2SeqDataset(VAL_DATA_DIR, tokenizer)
    
    # Get the vocabulary size from the tokenizer
    NUM_CLASSES = tokenizer.vocab_size
    print(f"Vocabulary size: {NUM_CLASSES}")

    # Load pretrained models
    bert_model_pretrained = BertModel.from_pretrained("bert-base-uncased")
    cnn_model_pretrained = models.resnet50(pretrained=True)

    # Initialize the Seq2Seq model, criterion, and optimizer
    model = Seq2SeqModel(NUM_CLASSES, bert_model_pretrained, cnn_model_pretrained).to(device)
    criterion = nn.CrossEntropyLoss(ignore_index=tokenizer.pad_token_id)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, collate_fn=pad_sequence_custom)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, collate_fn=pad_sequence_custom)

    # Start training
    train_model(model, train_loader, val_loader, criterion, optimizer, NUM_EPOCHS, device)

    # Load test data and labels from separate directories.
    test_dataset = Seq2SeqDataset(TEST_DATA_DIR, tokenizer, labels_dir=TEST_LABELS_DIR)
    
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, collate_fn=pad_sequence_custom)

    # After training, you can evaluate on the test set
    print("\nStarting evaluation on test set...")
    model.eval()
    test_total_loss = 0.0
    with torch.no_grad():
        for text_inputs, image_inputs, labels in test_loader:
            text_inputs = text_inputs.to(device)
            image_inputs = image_inputs.to(device)
            labels = labels.to(device)
            
            outputs = model(text_inputs, image_inputs, labels)
            loss = criterion(outputs.view(-1, outputs.size(-1)), labels.view(-1))
            test_total_loss += loss.item()
    
    test_avg_loss = test_total_loss / len(test_loader)
    print(f"Test Loss: {test_avg_loss:.4f}")
    print("\nEvaluation complete.")

    # Code to save the trained model
    model_save_path = "seq2seq_model.pth"
    try:
        torch.save(model.state_dict(), model_save_path)
        print(f"\nModel saved successfully at {model_save_path}")
    except Exception as e:
        print(f"\nError saving model: {e}")
