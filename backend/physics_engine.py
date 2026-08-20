import numpy as np

class FluidAcousticSimulator:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.obstruction_level = 0.0 # 0.0 to 100.0
        self.density = 1005.0 # kg/m^3 (approx CSF)
        self.viscosity = 0.0007 # Pa.s
        self.t = 0.0

    def set_obstruction(self, level):
        self.obstruction_level = max(0.0, min(100.0, float(level)))

    def generate_frame(self, frame_size=1024):
        time_steps = np.arange(frame_size) / self.sample_rate
        t_array = self.t + time_steps
        
        # 1. Biological artifacts (Heartbeat 1.2 Hz, Breathing 0.3 Hz)
        heartbeat = 0.1 * np.sin(2 * np.pi * 1.2 * t_array)
        breathing = 0.05 * np.sin(2 * np.pi * 0.3 * t_array)
        biological = heartbeat + breathing
        
        # 2. Ambient white noise (Sensor noise)
        ambient = np.random.normal(0, 0.01, frame_size)
        
        # Flow simulation based on obstruction
        norm_obs = self.obstruction_level / 100.0
        
        if norm_obs <= 0.30:
            # Laminar Flow: low-amplitude pink noise + low-freq hum
            # Simplified pink noise using normal distribution and a low-frequency hum (150 Hz)
            base_noise = np.random.normal(0, 0.05, frame_size) 
            hum = 0.02 * np.sin(2 * np.pi * 150 * t_array)
            signal = base_noise + hum + biological + ambient
            state = "Laminar"
            
        elif norm_obs <= 0.70:
            # Transitional / Turbulent Flow: vortex shedding (St ≈ 0.2)
            # Resonance peaks 1kHz - 4kHz
            base_noise = np.random.normal(0, 0.1, frame_size)
            strouhal_freq = 1000 + (norm_obs - 0.3) * 2500 * (1.0 / 0.4) # Scales 1000 to 3500 Hz
            resonance = 0.15 * np.sin(2 * np.pi * strouhal_freq * t_array)
            
            # Add some frequency modulation for realism
            modulation = np.sin(2 * np.pi * 10 * t_array)
            resonance *= (1 + 0.5 * modulation)
            
            signal = base_noise + resonance + biological + ambient
            state = "Transitional"
            
        else:
            # Severe Occlusion: High-freq hissing, cavitational micro-vibrations
            hiss = np.random.normal(0, 0.3 * norm_obs, frame_size)
            
            # Cavitation peaks at 4kHz - 8kHz
            cavitation_freq = 4000 + (norm_obs - 0.7) * 4000 * (1.0 / 0.3)
            cavitation = 0.2 * np.sin(2 * np.pi * cavitation_freq * t_array) * np.random.uniform(0.8, 1.2, frame_size)
            
            # Intermittent acoustic bursts
            bursts = np.zeros(frame_size)
            if np.random.random() < 0.05 * norm_obs: # 5% chance per frame to have a burst
                burst_len = min(frame_size, int(0.01 * self.sample_rate))
                bursts[:burst_len] = np.random.normal(0, 0.5, burst_len)
                
            signal = hiss + cavitation + bursts + biological + ambient
            state = "Turbulent"
            
        self.t += frame_size / self.sample_rate
        return signal, state
