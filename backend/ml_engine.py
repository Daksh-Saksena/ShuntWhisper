import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

class Autoencoder(nn.Module):
    def __init__(self, input_dim):
        super(Autoencoder, self).__init__()
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(True),
            nn.Linear(32, 16),
            nn.ReLU(True),
            nn.Linear(16, 8) # Latent space
        )
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(True),
            nn.Linear(16, 32),
            nn.ReLU(True),
            nn.Linear(32, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

class ShuntAnomalyDetector:
    def __init__(self, input_dim=10):
        self.input_dim = input_dim
        self.model = Autoencoder(input_dim)
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.01)
        self.threshold = 0.1
        self.is_calibrated = False

    def train_patient_baseline(self, normal_audio_samples, epochs=50):
        """Fits the Autoencoder exclusively on healthy baseline data."""
        if len(normal_audio_samples) == 0:
            return
            
        data = torch.FloatTensor(np.array(normal_audio_samples))
        
        self.model.train()
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            outputs = self.model(data)
            loss = self.criterion(outputs, data)
            loss.backward()
            self.optimizer.step()
            
        # Calculate reconstruction loss threshold (mu + 3*sigma)
        self.model.eval()
        with torch.no_grad():
            reconstructed = self.model(data)
            mse = torch.mean((data - reconstructed) ** 2, dim=1).numpy()
            mu = np.mean(mse)
            sigma = np.std(mse)
            self.threshold = float(mu + 3 * sigma)
            # Ensure a minimum threshold to avoid hyper-sensitivity
            self.threshold = max(self.threshold, 0.05)
            
        self.is_calibrated = True

    def predict(self, feature_vector):
        """Calculates reconstruction error and detects anomaly."""
        if not self.is_calibrated:
            return "UNAVAILABLE", 0.0, 0.0
            
        self.model.eval()
        with torch.no_grad():
            x = torch.FloatTensor(feature_vector).unsqueeze(0)
            reconstructed = self.model(x)
            mse = torch.mean((x - reconstructed) ** 2).item()
            
        # Calculate anomaly score mapped roughly between 0.0 and 1.0
        anomaly_score = min(1.0, mse / (self.threshold * 2.0))
        status = "ANOMALY_DETECTED" if mse > self.threshold else "NORMAL"
        
        return status, anomaly_score, mse

    def export_to_c_array(self):
        """Converts trained weights into a C header file (TinyML simulation)."""
        c_header = "/* ShuntWhisper TinyML Model Weights */\n"
        c_header += "#ifndef MODEL_DATA_H\n#define MODEL_DATA_H\n\n"
        
        for name, param in self.model.named_parameters():
            flat_data = param.data.numpy().flatten()
            array_str = ", ".join([f"{x:.6f}" for x in flat_data])
            var_name = name.replace('.', '_')
            c_header += f"const float {var_name}[{len(flat_data)}] = {{{array_str}}};\n\n"
            
        c_header += "#endif // MODEL_DATA_H\n"
        return c_header
