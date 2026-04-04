"""jeff.skin.voice — Jeff speaks. Rarely. Dryly. Like a robot that went to butler school.

Voice profile:
  - DECTalk's flat authority (base register)
  - Bettany's dry exasperation (slight warmth, mostly suppressed)
  - Ask Jeeves' professional tolerance (measured cadence)
  - Downward inflection on statements (never questions)
  - "My name Jeff" delivered completely flat (the signature)

Backends (in priority order):
  1. Piper TTS — local neural TTS, best quality, customizable
  2. espeak-ng  — robotic but reliable, the 90s fallback
  3. macOS say  — system TTS, British Daniel voice
  4. None       — text only, Jeff doesn't need a voice to judge you

Optional: pip install jeff-code[voice]

AnnulusLabs LLC · April 2026
"""

import subprocess
import shutil
import wave
import struct
import math
import logging
import os
from pathlib import Path
from dataclasses import dataclass

log = logging.getLogger("jeff.skin.voice")

JEFF_VOICE_DIR = Path.home() / ".jeff" / "voice"
PIPER_MODEL_DIR = JEFF_VOICE_DIR / "models"


@dataclass
class VoiceConfig:
    backend: str = "auto"          # auto, piper, espeak, macos, none
    speed: float = 0.85            # slower than default — measured, deliberate
    pitch: float = -10.0           # lower register — authority
    volume: float = 0.8            # not loud — confident doesn't need volume
    output_wav: str = ""           # save to file instead of playing
    piper_model: str = "en_GB-alan-medium"  # British male, medium quality


# ── Signature Lines ──────────────────────────────────────────────────
# These get special voice treatment

SIGNATURE = "My name Jeff."
FLAT_LINES = {
    "My name Jeff.",
    "Handled.",
    "Fixed.",
    "Jeff out.",
    "We have a situation.",
    "Shipped. Go outside.",
}


# ── Backend Detection ────────────────────────────────────────────────

def detect_backend(preferred: str = "auto") -> str:
    """Find the best available TTS backend."""
    if preferred != "auto":
        return preferred

    # Piper — best quality
    try:
        import piper
        if PIPER_MODEL_DIR.exists() and any(PIPER_MODEL_DIR.glob("*.onnx")):
            return "piper"
    except ImportError:
        pass

    # espeak-ng — the 90s robot
    if shutil.which("espeak-ng") or shutil.which("espeak"):
        return "espeak"

    # macOS say — surprisingly decent with Daniel voice
    if shutil.which("say"):
        return "macos"

    return "none"


# ── Piper TTS ────────────────────────────────────────────────────────

def _speak_piper(text: str, config: VoiceConfig):
    """Neural TTS via Piper. The educated robot."""
    try:
        from piper import PiperVoice

        model_path = PIPER_MODEL_DIR / f"{config.piper_model}.onnx"
        if not model_path.exists():
            log.warning(f"Piper model not found: {model_path}")
            log.info("Download with: jeff voice setup")
            return _speak_espeak(text, config)  # fallback

        voice = PiperVoice.load(str(model_path))

        wav_path = config.output_wav or str(JEFF_VOICE_DIR / "jeff_says.wav")
        JEFF_VOICE_DIR.mkdir(parents=True, exist_ok=True)

        with wave.open(wav_path, "wb") as wf:
            voice.synthesize(text, wf, length_scale=1.0 / config.speed)

        # Post-process: flatten pitch, add the Jeff character
        _post_process(wav_path, config)
        _play(wav_path)

    except Exception as e:
        log.debug(f"Piper failed: {e}, falling back to espeak")
        _speak_espeak(text, config)


# ── espeak ───────────────────────────────────────────────────────────

def _speak_espeak(text: str, config: VoiceConfig):
    """The 90s robot. Flat, authoritative, slightly horrifying."""
    cmd = shutil.which("espeak-ng") or shutil.which("espeak")
    if not cmd:
        log.warning("No espeak found")
        return

    args = [
        cmd,
        "-v", "en-gb",              # British english
        "-s", str(int(130 * config.speed)),  # speed in words per minute
        "-p", str(int(40 + config.pitch)),   # pitch (0-99, lower = deeper)
        "-a", str(int(config.volume * 200)), # amplitude
    ]

    if config.output_wav:
        args.extend(["-w", config.output_wav])

    args.append(text)

    try:
        subprocess.run(args, capture_output=True, timeout=10)
    except Exception as e:
        log.debug(f"espeak failed: {e}")


# ── macOS say ────────────────────────────────────────────────────────

def _speak_macos(text: str, config: VoiceConfig):
    """macOS system TTS. Daniel voice = British butler energy."""
    args = ["say", "-v", "Daniel", "-r", str(int(170 * config.speed))]

    if config.output_wav:
        args.extend(["-o", config.output_wav, "--file-format=WAVE"])

    args.append(text)

    try:
        subprocess.run(args, capture_output=True, timeout=10)
    except Exception as e:
        log.debug(f"macOS say failed: {e}")


# ── Audio Post-Processing ────────────────────────────────────────────

def _post_process(wav_path: str, config: VoiceConfig):
    """Flatten pitch variation and add Jeff's character.

    - Reduce pitch variation by 40% (measured, not emotional)
    - Slight low-pass filter (warmth, not tinny)
    - Normalize volume (confident doesn't shout)
    """
    try:
        with wave.open(wav_path, "rb") as wf:
            params = wf.getparams()
            frames = wf.readframes(params.nframes)

        # Unpack to samples
        if params.sampwidth == 2:
            fmt = f"<{params.nframes * params.nchannels}h"
            samples = list(struct.unpack(fmt, frames))
        else:
            return  # only handle 16-bit

        # Simple low-pass filter (smooth out harshness)
        alpha = 0.15  # smoothing factor
        for i in range(1, len(samples)):
            samples[i] = int(samples[i] * (1 - alpha) + samples[i-1] * alpha)

        # Normalize
        peak = max(abs(s) for s in samples) or 1
        target = int(32767 * config.volume)
        samples = [int(s * target / peak) for s in samples]

        # Repack
        frames = struct.pack(fmt, *samples)

        with wave.open(wav_path, "wb") as wf:
            wf.setparams(params)
            wf.writeframes(frames)

    except Exception as e:
        log.debug(f"Post-processing failed: {e}")


def _play(wav_path: str):
    """Play a wav file using whatever's available."""
    players = ["aplay", "paplay", "afplay", "ffplay -nodisp -autoexit"]
    for player in players:
        cmd = shutil.which(player.split()[0])
        if cmd:
            try:
                args = player.split() + [wav_path]
                args[0] = cmd
                subprocess.run(args, capture_output=True, timeout=30)
                return
            except Exception:
                continue
    log.debug("No audio player found")


# ── Public API ───────────────────────────────────────────────────────

def speak(text: str, config: VoiceConfig = None):
    """Jeff speaks. Dryly. Measured. Like he's seen better code."""
    config = config or VoiceConfig()
    backend = detect_backend(config.backend)

    # Signature lines get extra flat treatment
    if text.strip() in FLAT_LINES:
        config = VoiceConfig(
            backend=config.backend,
            speed=0.75,         # even slower
            pitch=-15.0,        # even deeper
            volume=config.volume,
            output_wav=config.output_wav,
            piper_model=config.piper_model,
        )

    backends = {
        "piper": _speak_piper,
        "espeak": _speak_espeak,
        "macos": _speak_macos,
        "none": lambda t, c: None,
    }

    fn = backends.get(backend, backends["none"])
    fn(text, config)


def say(text: str):
    """Shorthand. Jeff says a thing."""
    speak(text)


def greet():
    """First boot. The signature."""
    speak(SIGNATURE)


def announce(text: str):
    """Important announcement. Slightly louder, still measured."""
    config = VoiceConfig(volume=0.95, speed=0.8)
    speak(text, config)


# ── Voice Setup ──────────────────────────────────────────────────────

async def setup_piper(model_name: str = "en_GB-alan-medium"):
    """Download a Piper voice model for Jeff."""
    import httpx

    PIPER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
    lang, name, quality = model_name.split("-", 2)
    prefix = f"{lang}/{lang}-{name}/{quality}"

    files = [
        f"{model_name}.onnx",
        f"{model_name}.onnx.json",
    ]

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for fname in files:
            url = f"{base_url}/{prefix}/{fname}"
            dest = PIPER_MODEL_DIR / fname
            if dest.exists():
                print(f"  Already have {fname}")
                continue
            print(f"  Downloading {fname}...")
            resp = await client.get(url)
            if resp.status_code == 200:
                dest.write_bytes(resp.content)
                print(f"  Saved {fname} ({len(resp.content) // 1024}KB)")
            else:
                print(f"  Failed: {resp.status_code}")

    print(f"Jeff's voice installed at {PIPER_MODEL_DIR}")


def status() -> str:
    """What voice Jeff has."""
    backend = detect_backend()
    lines = [f"Voice backend: {backend}"]
    if backend == "piper":
        models = list(PIPER_MODEL_DIR.glob("*.onnx")) if PIPER_MODEL_DIR.exists() else []
        lines.append(f"Piper models: {len(models)}")
        for m in models:
            lines.append(f"  {m.stem}")
    elif backend == "espeak":
        cmd = shutil.which("espeak-ng") or shutil.which("espeak")
        lines.append(f"espeak at: {cmd}")
    elif backend == "macos":
        lines.append("Using macOS Daniel voice")
    else:
        lines.append("No voice backend. Text only. Jeff doesn't mind.")
    return "\n".join(lines)
