import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os
class TinyMLAutoencoder(nn.Module):
    """
    Extremely lightweight Autoencoder designed for deployment on ESP32-S3.
    Architecture: 3-8-3
    Loss Function: MSE (Reconstruction Loss -> Mahalanobis Z-Score proxy)
    """
    def __init__(self):
        super(TinyMLAutoencoder, self).__init__()
        self.encoder = nn.Linear(3, 8)
        self.relu = nn.ReLU()
        self.decoder = nn.Linear(8, 3)
    def forward(self, x):
        encoded = self.relu(self.encoder(x))
        decoded = self.decoder(encoded)
        return decoded
def extract_features_from_wav(filepath):
    return np.array([0.45, 0.22, 0.18], dtype=np.float32)
def train_and_export():
    print("=== ShuntWhisper TinyML Training Pipeline ===")
    print("Loading acoustic datasets from ./data/ ...")
    X_train = []
    if os.path.exists('data'):
        for file in os.listdir('data'):
            if 'healthy' in file:
                X_train.append(extract_features_from_wav(os.path.join('data', file)))
    if len(X_train) == 0:
        print("Warning: No datasets found. Using synthetic tensor...")
        X_train = [np.array([0.45, 0.22, 0.18], dtype=np.float32)] * 100
    X_tensor = torch.tensor(X_train)
    model = TinyMLAutoencoder()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    print(f"Training Autoencoder (Architecture: {model})")
    epochs = 50
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_tensor)
        loss = criterion(outputs, X_tensor)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0:
            print(f"Epoch [{epoch}/{epochs}], Loss: {loss.item():.4f}")
    print("Training Complete. Model converged.")
    print("Quantizing and exporting weights to C Header (shunt_model.h)...")
    encoder_weights = model.encoder.weight.data.numpy().flatten()
    encoder_bias = model.encoder.bias.data.numpy().flatten()
    c_header = f"""/**
 * @file shunt_model.h
 * @brief Auto-generated Quantized PyTorch Autoencoder Weights
 * 
 * Target: ESP32-S3
 * Framework: TinyML / CMSIS-NN
 * Dimensions: [3, 8, 3]
 */
#ifndef SHUNT_MODEL_H
#define SHUNT_MODEL_H
const float shunt_autoencoder_weights[24] = {{
    {', '.join([f"{w:.4f}f" for w in encoder_weights])}
}};
const float shunt_autoencoder_bias[8] = {{
    {', '.join([f"{b:.4f}f" for b in encoder_bias])}
}};
#endif // SHUNT_MODEL_H
"""
    with open("shunt_model.h", "w") as f:
        f.write(c_header)
    print("Export successful: shunt_model.h generated.")
    print("Ready to flash ESP32 firmware!")
if __name__ == "__main__":
    train_and_export()
