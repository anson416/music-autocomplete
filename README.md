# Music Auto-complete

Repository for AIST2010 group project.

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Install [FFmpeg](https://ffmpeg.org/download.html)

3. Download the [default soundfont](https://drive.google.com/file/d/1hG9ZS937AWSYWydMIwA4CA1Zu0DEw6EZ/view?usp=share_link) to `api/musgen`.

4. Install and start Docker image by following the instructions on [this page](https://github.com/anson416/music-autocomplete/tree/main/api)

5. Start program:

   ```bash
   python main.py
   ```

## Controls (Piano Roll)

### Grid

- Add notes by double-clicking on the grid
- Remove notes by right-clicking existing notes
- Extend note length by dragging the right end of the note
- Change note pitch and timing by dragging the left end/center of the note
- Scroll to move up and down the grid
- Hold Shift while scrolling to move left and right along the grid

### Tempo

- See the tempo of the music in the top-left corner
- Increase/Decrease tempo using the plus/minus buttons

### Ruler

- Numbers indicate which bars of music are shown on click
- Left click on the ruler to set the playhead

### Velocity Slider

- Click on a note to see its velocity in the slider
- Click anywhere on the slider to modify the velocity

## Importing MIDI / Audio files

### MIDI

- Click on the "MIDI" button to import MIDI files
  - For Windows: Select a file from the file explorer shown up
  - For MacOS: Put the .mid file in the `inputs` folder before clicking the button. Do not put more than one .mid file in the folder

### Audio Files

#### Transcription with Librosa

- Click on the "Librosa" button to import wav / mp3 files with our own transcription method
  - For Windows: Select a file from the file explorer shown up
  - For MacOS: Put the .wav / .mp3 file in the `inputs` folder before clicking the button. Do not put more than one .wav / .mp3 file in the folder

#### Transcription with Transformer

- Click on the "MT3" button to import .wav / .mp3 files with auto-transcription provided by Magenta model
  - For Windows: Select a file from the file explorer shown up
  - Works on Windows only

### Recording your own sound

- Click on the "Record" button to start recording, stop the recording by clicking once more
  - The sound will be automatically transcripted and placed onto the piano roll
  - Works for Windows only

## Music Extension

- Click on the left/right arrow to select by which method the melody will be extended
- Move the slider to adjust the duration of extension
- Click on the "Generate" button to extend melody

## Sound Synthesis

### GANSynth

- Click on the left/right arrow to change duration of each instrument (in seconds)
- Click on the "GANSynth" button to generate WAV

### Playback

- Click on the "Quick Play" button to play notes in the piano roll, starting from the playhead
- Click on the "Play" button to play notes using GANSynth

## Export

- Click on the "Export MIDI" button to output a midi file. (For MacOS: midi file in stored in `export` folder automatically)
- Click on the "Export WAV" button to output a wav file. (For MacOS: wav file in stored in `export` folder automatically)
