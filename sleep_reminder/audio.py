"""
Soothing audio synthesizer and chime manager.
Generates calming harmonic bell tones in memory using standard Python wave & math,
played via Windows Sound API (winsound) asynchronously.
"""

from __future__ import annotations
import io
import math
import struct
import sys
from typing import List, Tuple

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    winsound = None
    WINSOUND_AVAILABLE = False


def _synthesize_bell_chime(
    notes: List[Tuple[float, float, float]], # list of (start_sec, freq_hz, volume)
    duration: float = 2.0,
    sample_rate: int = 44100,
    decay_rate: float = 3.2,
) -> bytes:
    """
    Synthesizes a warm, soothing acoustic bell chord in WAV format in memory.
    notes: list of (start_time, frequency, amplitude_factor)
    """
    total_samples = int(sample_rate * duration)
    frames = bytearray()

    for i in range(total_samples):
        t = i / sample_rate
        sample_val = 0.0

        for start, freq, amp in notes:
            if t >= start:
                dt = t - start
                # Harmonic fundamental + soft 2nd harmonic (octave) for warmth
                env = math.exp(-dt * decay_rate)
                tone = math.sin(2.0 * math.pi * freq * dt) + 0.3 * math.sin(4.0 * math.pi * freq * dt)
                sample_val += tone * env * amp

        # Soft clipping limiter
        sample_val = max(-1.0, min(1.0, sample_val * 0.4))
        int_sample = int(sample_val * 32767.0)
        frames.extend(struct.pack("<h", int_sample))

    buf = io.BytesIO()
    import wave
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)

    return buf.getvalue()


class SoundManager:
    """Manages audio cues for wind-down and bedtime."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._cache: dict[str, bytes] = {}
        self._pre_generate_sounds()

    def _pre_generate_sounds(self) -> None:
        # 1. Gentle Wind-down Arpeggio: F4 (349.2), A4 (440.0), C5 (523.2), E5 (659.3)
        self._cache["wind_down"] = _synthesize_bell_chime(
            notes=[
                (0.00, 349.23, 0.7),
                (0.20, 440.00, 0.7),
                (0.40, 523.25, 0.8),
                (0.60, 659.25, 0.9),
            ],
            duration=2.5,
            decay_rate=2.6,
        )

        # 2. Bedtime Calming Lullaby Chord: C4 (261.6), G4 (392.0), C5 (523.2), E5 (659.3)
        self._cache["bedtime"] = _synthesize_bell_chime(
            notes=[
                (0.00, 261.63, 0.8),
                (0.25, 392.00, 0.8),
                (0.50, 523.25, 0.85),
                (0.75, 659.25, 0.9),
                (1.00, 783.99, 0.8),
            ],
            duration=3.2,
            decay_rate=2.2,
        )

        # 3. Snooze / Confirmation Sound: Gentle duo
        self._cache["snooze"] = _synthesize_bell_chime(
            notes=[
                (0.00, 440.00, 0.6),
                (0.18, 554.37, 0.7),
            ],
            duration=1.2,
            decay_rate=4.0,
        )

    def play(self, sound_name: str) -> None:
        """Plays the designated sound asynchronously if audio is enabled."""
        if not self.enabled or not WINSOUND_AVAILABLE:
            return

        wav_bytes = self._cache.get(sound_name)
        if not wav_bytes:
            return

        try:
            # winsound.SND_MEMORY (4) | winsound.SND_ASYNC (1)
            flags = winsound.SND_MEMORY | winsound.SND_ASYNC
            winsound.PlaySound(wav_bytes, flags)
        except Exception:
            # Fallback to standard beep if audio device fails
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def play_wind_down(self) -> None:
        self.play("wind_down")

    def play_bedtime(self) -> None:
        self.play("bedtime")

    def play_snooze(self) -> None:
        self.play("snooze")
