import os
import numpy as np
import scipy.io.wavfile as wavfile

class DatasetSynthesizer:
    """
    Generates synthetic high-fidelity fluid acoustic datasets (.wav)
    to emulate healthy and strictured Hydrocephalus shunts for ML training.
    """
    def __init__(self, sample_rate=16000, duration=5.0):
        self.sample_rate = sample_rate
        self.duration = duration
        self.t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    def generate_healthy_flow(self):
        """Generates laminar CSF flow acoustics (Healthy)."""
        base_freq = 150.0 # Base resonance of silicone tube
        laminar_wave = 0.6 * np.sin(2 * np.pi * base_freq * self.t)
        pulse = 0.15 * np.sin(2 * np.pi * 1.2 * self.t) # Heartbeat pressure drift
        noise = np.random.normal(0, 0.02, len(self.t))
        return np.clip(laminar_wave + pulse + noise, -1.0, 1.0)

    def generate_stricture_flow(self, severity=0.8):
        """Generates turbulent CSF flow with high-frequency micro-cavitation (Stricture)."""
        healthy = self.generate_healthy_flow()
        
        # Inject high-frequency chaotic resonance (Reynolds number > 4000 equivalent)
        turbulence = (np.random.rand(len(self.t)) - 0.5) * 1.5 * severity
        cavitation = 0.4 * severity * np.sin(2 * np.pi * 3500 * self.t) * (np.random.rand(len(self.t)) > 0.5)
        
        return np.clip(healthy + turbulence + cavitation, -1.0, 1.0)

    def export_wav(self, filename, data):
        # Convert float32 to int16 for wav format
        scaled = np.int16(data * 32767)
        wavfile.write(filename, self.sample_rate, scaled)
        print(f"Exported {filename} ({len(data)} samples @ {self.sample_rate}Hz)")

if __name__ == "__main__":
    print("=== ShuntWhisper Dataset Synthesizer ===")
    os.makedirs("data", exist_ok=True)
    synth = DatasetSynthesizer()
    
    print("Generating Healthy Baseline Dataset...")
    for i in range(10):
        synth.export_wav(f"data/healthy_{i}.wav", synth.generate_healthy_flow())
        
    print("Generating Stricture Anomaly Dataset...")
    for i in range(10):
        synth.export_wav(f"data/stricture_{i}.wav", synth.generate_stricture_flow(severity=0.7 + np.random.rand()*0.3))
    
    print("Dataset generation complete. Ready for ML Training.")
