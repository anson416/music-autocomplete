# API for Music Generation

## Installation

1. Install [Docker](https://docs.docker.com/engine/install/)

2. Change directory to here (i.e., `cd api`)

3. Build an image for `musgen`:

   ```bash
   docker build --no-cache --build-arg arch=<arch> -t musgen:<tag> ./musgen
   ```

   `<arch>`: ARM64 architecture: `arm64`; AMD64 architecture: `amd64`.

   `<tag>`: Anything you want to put here, such as `v1`, `test` etc.

4. Build an image for `mustrans` (only works on AMD64):

   ```bash
   docker build --no-cache --build-arg arch=amd64 -t mustrans:<tag> ./mustrans
   ```

5. Create and run containers:

   ```bash
   docker run -p 8100:8000 -it --name musgen musgen:<tag>
   docker run -p 8200:8000 -it --name mustrans mustrans:<tag>
   ```

6. Test (and download models):

   ```bash
   python test_magenta_rnn_api.py
   python test_gansynth_api.py
   python test_mt_transformers_api.py
   ```

7. Stop container:

   ```bash
   docker stop <container_name_or_id>
   ```

8. Restart stopped container:

   ```bash
   docker start -i <container_name_or_id>
   ```

   You may also want to attach to it:

   ```bash
   docker attach <container_name_or_id>
   ```

9. Remove container:

   ```bash
   docker rm <container_name_or_id>
   ```

10. Remove image:

    ```bash
    docker image rm <image_name_or_id>:<tag>
    ```

## API Usage (for developers)

### Melody RNN

Input: Model, list of notes, QPM, duration to extend, temperature (default: 1)

Output: List of notes (containing only the highest note in each chord)

```python
import json
import requests

# Models: basic_rnn, mono_rnn, lookback_rnn, attention_rnn
model = "basic_rnn"
notes = [
    {"note": 79, "start_time": 0.0, "duration": 3.5, "velocity": 80},
    {"note": 74, "start_time": 0.0, "duration": 3.5, "velocity": 70},
    {"note": 71, "start_time": 0.0, "duration": 3.5, "velocity": 60},
    {"note": 78, "start_time": 3.5, "duration": 0.25, "velocity": 70},
    {"note": 79, "start_time": 3.75, "duration": 0.25, "velocity": 70},
    {"note": 78, "start_time": 4, "duration": 2, "velocity": 70},
    {"note": 71, "start_time": 4, "duration": 4, "velocity": 80},
    {"note": 83, "start_time": 6, "duration": 2, "velocity": 70},
    {"note": 64, "start_time": 6, "duration": 2, "velocity": 60},
]
qpm = 60
extend_duration = 20
temperature = 1

# Output
response = requests.request(
    "POST",
    f"http://localhost:8100/melody_rnn/{model}",
    params={
        "qpm": qpm,
        "extend_duration": extend_duration,
        "temperature": temperature,
    },
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
    },
    data=json.dumps(notes),
).json()
```

### Performance RNN

Input: Model, list of notes, QPM, duration to extend, temperature (default: 1)

Output: List of notes

```python
import json
import requests

# Models: performance, performance_with_dynamics, 
#         performance_with_dynamics_and_modulo_encoding, density_conditioned_performance_with_dynamics, 
#         pitch_conditioned_performance_with_dynamics, multiconditioned_performance_with_dynamics
model = "performance_with_dynamics"
notes = [
    {"note": 79, "start_time": 0.0, "duration": 3.5, "velocity": 80},
    {"note": 74, "start_time": 0.0, "duration": 3.5, "velocity": 70},
    {"note": 71, "start_time": 0.0, "duration": 3.5, "velocity": 60},
    {"note": 78, "start_time": 3.5, "duration": 0.25, "velocity": 70},
    {"note": 79, "start_time": 3.75, "duration": 0.25, "velocity": 70},
    {"note": 78, "start_time": 4, "duration": 2, "velocity": 70},
    {"note": 71, "start_time": 4, "duration": 4, "velocity": 80},
    {"note": 83, "start_time": 6, "duration": 2, "velocity": 70},
    {"note": 64, "start_time": 6, "duration": 2, "velocity": 60},
]
qpm = 60
extend_duration = 20
temperature = 0.5

# Output
response = requests.request(
    "POST",
    f"http://localhost:8100/performance_rnn/{model}",
    params={
        "qpm": qpm,
        "extend_duration": extend_duration,
        "temperature": temperature,
    },
    headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
    },
    data=json.dumps(notes),
).json()
```

### GANSynth

Input: Path to MIDI file, seconds per instrument (default: 5), sample rate (default: 16000)

Output: WAV file

```python
import mimetypes
from pathlib import Path
import numpy as np
import requests
from scipy.io import wavfile

def save_wav(audio: np.array, file_name, sample_rate: int = 16000):
    wavfile.write(file_name, sample_rate, audio.astype("float32"))

midi_path = "./demo/demo.mid"
seconds_per_instrument = 5.5
sample_rate = 16000

with open(midi_path, "rb") as midi_file:
    response = requests.request(
        "POST",
        "http://localhost:8100/gansynth",
        params={
            "seconds_per_instrument": seconds_per_instrument,
            "sample_rate": sample_rate,
        },
        headers={
            "Accept": "application/json",
        },
        files={
            "midi_file": (Path(midi_path).name, midi_file, mimetypes.guess_type(midi_path)[0]),
        },
    ).json()

# Output
wav_path = f"gansynth_{Path(midi_path).stem}.wav"
save_wav(np.array(response), wav_path)
```

### Music Transcription with Transformers

Input: Model, path to audio file (WAV, MP3) , sample rate (default: 16000)

Output: List of notes

```python
import mimetypes
from pathlib import Path
import requests

# Models: ismir2021, mt3
model = "mt3"
audio_path = "./demo/demo.wav"
sample_rate = 16000

with open(audio_path, "rb") as audio_file:
    # Output
    response = requests.request(
        "POST",
        f"http://localhost:8200/music_transcription_with_transformers/{model}",
        params={
            "sample_rate": sample_rate,
        },
        headers={
            "Accept": "application/json",
        },
        files={
            "audio_file": (Path(audio_path).name, audio_file, mimetypes.guess_type(audio_path)[0]),
        },
    ).json()
```

### MIDI to WAV

Input: Path to MIDI file

Output: WAV file

```python
import mimetypes
from pathlib import Path
import numpy as np
import requests
from scipy.io import wavfile

def save_wav(audio: np.array, file_name, sample_rate: int = 44100):
    wavfile.write(file_name, sample_rate, audio)

midi_path = "./demo/demo.mid"

with open(midi_path, "rb") as midi_file:
    response = requests.request(
        "POST",
        "http://localhost:8100/midi2wav",
        headers={
            "Accept": "application/json",
        },
        files={
            "midi_file": (Path(midi_path).name, midi_file, mimetypes.guess_type(midi_path)[0]),
        },
    ).json()

# Output
wav_path = f"midi2wav_{Path(midi_path).stem}.wav"
save_wav(np.array(response["audio"], dtype=response["dtype"]), wav_path, sample_rate=response["sample_rate"])
```
