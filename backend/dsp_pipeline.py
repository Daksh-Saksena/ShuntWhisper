import numpy as np
from scipy.signal import butter, lfilter, iirnotch

class AcousticDSP:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        
        # 4th-order Butterworth bandpass (100 Hz to 8000 Hz)
        nyq = 0.5 * sample_rate
        self.low = 100.0 / nyq
        self.high = min(8000.0 / nyq, 0.99)
        self.b_band, self.a_band = butter(4, [self.low, self.high], btype='band')
        
        # Notch filter for 50 Hz electrical hum
        self.b_notch, self.a_notch = iirnotch(50.0, 30.0, sample_rate)

    def process_frame(self, frame):
        # 1. Filtering
        filtered = lfilter(self.b_notch, self.a_notch, frame)
        filtered = lfilter(self.b_band, self.a_band, filtered)
        
        # 2. Windowing (Hanning window over frame)
        windowed = filtered * np.hanning(len(filtered))
        
        # 3. Spectral Transformations (FFT)
        fft_complex = np.fft.rfft(windowed)
        fft_mag = np.abs(fft_complex)
        freqs = np.fft.rfftfreq(len(windowed), 1 / self.sample_rate)
        
        # Downsample FFT to 32 buckets for UI rendering
        buckets = 32
        # Drop the DC component, segment the rest
        usable_mag = fft_mag[1:]
        bin_size = max(1, len(usable_mag) // buckets)
        fft_spectrum = [float(np.mean(usable_mag[i*bin_size : (i+1)*bin_size])) for i in range(buckets)]
        
        # 4. Feature Extraction
        power_spectrum = fft_mag ** 2
        sum_power = np.sum(power_spectrum) + 1e-10
        
        # Spectral Centroid
        centroid = np.sum(freqs * power_spectrum) / sum_power
        
        # Spectral Flatness
        geometric_mean = np.exp(np.mean(np.log(power_spectrum + 1e-10)))
        arithmetic_mean = np.mean(power_spectrum) + 1e-10
        flatness = geometric_mean / arithmetic_mean
        
        # Spectral Rolloff (85%)
        cum_sum_power = np.cumsum(power_spectrum)
        rolloff_idx = np.where(cum_sum_power >= 0.85 * sum_power)[0][0]
        rolloff = freqs[rolloff_idx]
        
        # Lightweight pseudo-MFCCs (energy in mel-spaced bands) using raw buckets
        # Combined feature vector for ML model (10 dimensions)
        features = np.array([centroid, flatness, rolloff] + fft_spectrum[:7])
        
        return {
            "fft_spectrum": fft_spectrum,
            "features": features
        }
