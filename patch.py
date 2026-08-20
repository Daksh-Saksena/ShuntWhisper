with open("/Users/mayanksaksena2024icloud.com/Desktop/whisper/index.html", "r") as f:
    lines = f.readlines()
out = []
in_anim_loop = False
for line in lines:
    if "// Animation Loop" in line:
        in_anim_loop = True
        out.append(line)
        out.append("""        // --- WebSocket Connection & Backend Integration ---
        const ws = new WebSocket("ws://127.0.0.1:8000/ws/telemetry");
        ws.onopen = () => {
            console.log("Connected to ShuntWhisper Backend");
            // Sync initial slider state
            updateObstruction(slider.value);
        };
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (!width) resizeCanvas();
            const val = parseInt(data.obstruction_level);
            sliderValueDisplay.innerText = val;
            // --- Update UI Text & States ---
            if (data.status === "NORMAL") {
                diagPanel.className = "glass rounded-2xl p-8 flex-grow flex flex-col justify-center items-center text-center transition-all duration-500 glow-normal relative overflow-hidden";
                statusIcon.innerText = "🟢";
                statusIcon.style.transform = "scale(1)";
                statusText.innerText = "FLOW STATUS: NORMAL";
                statusText.className = "text-2xl md:text-3xl font-extrabold mb-3 neon-text-green text-emerald-400 transition-colors duration-300";
                statusSubtext.innerText = `Acoustic signature matches personalized baseline. ${data.fluid_state} fluid dynamics detected.`;
                let confidence = Math.max(0, (1.0 - data.anomaly_score)) * 100;
                confScore.innerText = confidence.toFixed(1) + "%";
                confScore.className = "mono text-emerald-400 font-bold text-xl";
                confBar.style.width = confidence + "%";
                confBar.className = "bg-gradient-to-r from-emerald-600 to-emerald-400 h-full rounded-full transition-all duration-300";
                headerBar.className = "absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 via-blue-500 to-emerald-500 opacity-70";
                logoIcon.classList.remove('text-red-500');
                logoIcon.classList.add('text-emerald-400');
                subtitleText.classList.remove('text-red-400');
                subtitleText.classList.add('text-emerald-400');
                diagGlow1.className = "absolute -top-10 -right-10 w-32 h-32 bg-emerald-500/10 rounded-full blur-3xl transition-colors duration-500";
                diagGlow2.className = "absolute -bottom-10 -left-10 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl transition-colors duration-500";
                recPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75";
                recDot.className = "relative inline-flex rounded-full h-3 w-3 bg-emerald-500";
            } else {
                diagPanel.className = "glass rounded-2xl p-8 flex-grow flex flex-col justify-center items-center text-center transition-all duration-500 glow-alert relative overflow-hidden";
                statusIcon.innerText = "🔴";
                let jitterX = (Math.random() - 0.5) * 8 * data.anomaly_score;
                let jitterY = (Math.random() - 0.5) * 8 * data.anomaly_score;
                statusIcon.style.transform = `scale(1.15) translate(${jitterX}px, ${jitterY}px)`;
                statusText.innerText = "FLOW ANOMALY DETECTED";
                statusText.className = "text-2xl md:text-3xl font-extrabold mb-3 neon-text-red text-red-500 transition-colors duration-300";
                statusSubtext.innerText = `${data.fluid_state} flow detected. High reconstruction loss (${data.reconstruction_loss.toFixed(4)}). Immediate review required.`;
                let confidence = data.anomaly_score * 100;
                confScore.innerText = confidence.toFixed(1) + "%";
                confScore.className = "mono text-red-400 font-bold text-xl";
                confBar.style.width = confidence + "%";
                confBar.className = "bg-gradient-to-r from-red-600 to-red-400 h-full rounded-full transition-all duration-300 shadow-[0_0_10px_rgba(239,68,68,0.8)]";
                headerBar.className = "absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500 via-orange-500 to-red-500 opacity-90 animate-pulse";
                logoIcon.classList.remove('text-emerald-400');
                logoIcon.classList.add('text-red-500');
                subtitleText.classList.remove('text-emerald-400');
                subtitleText.classList.add('text-red-400');
                diagGlow1.className = "absolute -top-10 -right-10 w-32 h-32 bg-red-500/20 rounded-full blur-3xl transition-colors duration-500";
                diagGlow2.className = "absolute -bottom-10 -left-10 w-32 h-32 bg-orange-500/20 rounded-full blur-3xl transition-colors duration-500";
                recPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75";
                recDot.className = "relative inline-flex rounded-full h-3 w-3 bg-red-500";
            }
            // --- Update Waveform Array ---
            for (let point of data.raw_waveform) {
                waveHistory.push(point * 150); // Scale multiplier for visuals
            }
            if (waveHistory.length > maxHistory) {
                waveHistory = waveHistory.slice(waveHistory.length - maxHistory);
            }
            // --- Draw Live Waveform ---
            ctx.clearRect(0, 0, width, height);
            ctx.beginPath();
            if (val < 50) {
                ctx.strokeStyle = '#34d399';
                ctx.shadowColor = 'rgba(16, 185, 129, 0.8)';
                ctx.lineWidth = 2.5;
                ctx.shadowBlur = 12;
            } else {
                ctx.strokeStyle = '#ef4444';
                ctx.shadowColor = 'rgba(239, 68, 68, 0.9)';
                ctx.lineWidth = 2 + ((val/100) * 2.5);
                ctx.shadowBlur = 15 + ((val/100) * 10);
            }
            const centerY = height / 2;
            const stepX = width / (maxHistory - 1);
            for (let i = 0; i < waveHistory.length; i++) {
                let x = i * stepX;
                let y = centerY - waveHistory[i];
                let padding = 10;
                y = Math.max(padding, Math.min(height - padding, y));
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.stroke();
            // Glow head
            const lastY = Math.max(10, Math.min(height - 10, centerY - waveHistory[waveHistory.length - 1]));
            ctx.beginPath();
            ctx.arc(width, lastY, val < 50 ? 4 : 6, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff';
            ctx.fill();
            ctx.stroke();
            // --- Update Spectrogram ---
            const fft = data.fft_spectrum;
            for (let i = 0; i < numBars; i++) {
                let fftIndex = Math.floor((i / numBars) * fft.length);
                let rawEnergy = fft[fftIndex] || 0;
                // Adjust scaling specifically for UI
                let barHeight = Math.min(100, Math.max(2, rawEnergy * 8)); 
                if (val < 50) {
                    bars[i].className = 'flex-1 bg-gradient-to-t from-emerald-600 to-emerald-400 rounded-t-sm transition-all duration-75';
                    bars[i].style.boxShadow = '0 -4px 10px rgba(16, 185, 129, 0.3)';
                    bars[i].style.opacity = '0.9';
                } else {
                    if (barHeight > 65) {
                        bars[i].className = 'flex-1 bg-gradient-to-t from-red-600 to-red-400 rounded-t-sm transition-all duration-75';
                        bars[i].style.boxShadow = '0 -5px 15px rgba(239, 68, 68, 0.6)';
                    } else if (barHeight > 35) {
                        bars[i].className = 'flex-1 bg-gradient-to-t from-orange-600 to-orange-400 rounded-t-sm transition-all duration-75';
                        bars[i].style.boxShadow = '0 -5px 15px rgba(249, 115, 22, 0.5)';
                    } else {
                        bars[i].className = 'flex-1 bg-gradient-to-t from-yellow-600 to-yellow-400 rounded-t-sm transition-all duration-75';
                        bars[i].style.boxShadow = '0 -4px 10px rgba(234, 179, 8, 0.4)';
                    }
                    bars[i].style.opacity = '1';
                }
                bars[i].style.height = `${barHeight}%`;
            }
        };
        ws.onclose = () => {
            console.warn("Disconnected from Backend.");
            statusText.innerText = "CONNECTION LOST";
            statusText.className = "text-2xl md:text-3xl font-extrabold mb-3 text-slate-500 transition-colors duration-300";
            statusSubtext.innerText = "WebSocket disconnected. Please ensure the backend is running.";
            diagPanel.className = "glass rounded-2xl p-8 flex-grow flex flex-col justify-center items-center text-center transition-all duration-500 border-slate-700 relative overflow-hidden";
            statusIcon.innerText = "🔌";
            statusIcon.style.transform = "scale(1)";
        };
        // Handle Slider Changes via HTTP API
        let debounceTimer;
        function updateObstruction(level) {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                fetch("http://127.0.0.1:8000/api/set-obstruction", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ obstruction_level: parseFloat(level) })
                }).catch(e => console.error("Error setting obstruction:", e));
            }, 50);
        }
        slider.addEventListener('input', (e) => {
            sliderValueDisplay.innerText = e.target.value;
            updateObstruction(e.target.value);
        });
""")
        continue
    if in_anim_loop:
        if "// Start animation loop" in line:
            in_anim_loop = False
        continue
    out.append(line)
with open("/Users/mayanksaksena2024icloud.com/Desktop/whisper/index.html", "w") as f:
    f.writelines(out)
