# Recursive Audio to MP3 Converter

A Python utility that recursively scans a source directory and creates an MP3 library in a target directory.

The user chooses the desired MP3 bitrate:

- **128 kbps**
- **192 kbps**
- **256 kbps**

The script preserves the source folder structure, attempts to preserve audio metadata and embedded album artwork, and skips files that already exist in the target directory.

## Features

- Recursively scans the source directory.
- Supports common audio formats.
- User-selectable output bitrate: **128, 192, or 256 kbps**.
- MP3 files at or below the selected bitrate are copied unchanged.
- MP3 files above the selected bitrate are re-encoded to the selected bitrate.
- Non-MP3 files are converted to MP3 at the selected bitrate.
- Preserves the source folder hierarchy.
- Attempts to preserve:
  - Title
  - Artist
  - Album
  - Album artist
  - Genre
  - Track number
  - Disc number
  - Date/year
  - Comments
  - Other compatible metadata
  - Embedded album artwork
- Skips processing when the corresponding target `.mp3` already exists.
- Never modifies or deletes source files.
- Can safely be run repeatedly.

## Requirements

### Software

- Python **3.9+**
- FFmpeg
- FFprobe

`ffmpeg` and `ffprobe` must be available through the system `PATH`.

### Python Packages

No third-party Python packages are required.

The script uses only the Python standard library.

Therefore, `requirements.txt` does not contain any Python package dependencies.

## Installing FFmpeg

### Windows

Install FFmpeg and add its `bin` directory to your system `PATH`.

Verify from a new Command Prompt or PowerShell window:

```powershell
ffmpeg -version
ffprobe -version
```

Both commands should display version information.

### Linux

Debian/Ubuntu:

```bash
sudo apt update
sudo apt install ffmpeg
```

Verify:

```bash
ffmpeg -version
ffprobe -version
```

### macOS

Using Homebrew:

```bash
brew install ffmpeg
```

Verify:

```bash
ffmpeg -version
ffprobe -version
```

## Installation

Project structure:

```text
audio-converter/
├── main.py
├── README.md
└── requirements.txt
```

No Python packages need to be installed.

If desired:

```bash
pip install -r requirements.txt
```

The file is intentionally empty of package dependencies because the application uses Python's standard library.

## Usage

Run:

```bash
python main.py
```

The program asks for:

```text
Source Path:
Target Path:
```

It then asks you to choose the output bitrate:

```text
Select target MP3 bitrate:

  1. 128 kbps
  2. 192 kbps
  3. 256 kbps

Enter choice (1-3):
```

### Example

```text
Source Path: D:\Music
Target Path: D:\Converted Music

Select target MP3 bitrate:

  1. 128 kbps
  2. 192 kbps
  3. 256 kbps

Enter choice (1-3): 2
```

The selected target bitrate is therefore **192 kbps**.

## Bitrate Rules

The selected bitrate controls the maximum bitrate used for output.

### Example: selecting 128 kbps

```text
64 kbps MP3   -> copy unchanged
96 kbps MP3   -> copy unchanged
128 kbps MP3  -> copy unchanged
192 kbps MP3  -> convert to 128 kbps
256 kbps MP3  -> convert to 128 kbps
320 kbps MP3  -> convert to 128 kbps
FLAC          -> convert to 128 kbps MP3
WAV           -> convert to 128 kbps MP3
M4A           -> convert to 128 kbps MP3
```

### Example: selecting 192 kbps

```text
128 kbps MP3  -> copy unchanged
192 kbps MP3  -> copy unchanged
256 kbps MP3  -> convert to 192 kbps
320 kbps MP3  -> convert to 192 kbps
FLAC          -> convert to 192 kbps MP3
WAV           -> convert to 192 kbps MP3
M4A           -> convert to 192 kbps MP3
```

### Example: selecting 256 kbps

```text
128 kbps MP3  -> copy unchanged
192 kbps MP3  -> copy unchanged
256 kbps MP3  -> copy unchanged
320 kbps MP3  -> convert to 256 kbps
FLAC          -> convert to 256 kbps MP3
WAV           -> convert to 256 kbps MP3
M4A           -> convert to 256 kbps MP3
```

The script does **not** up-convert a lower-quality MP3.

For example, selecting 256 kbps does not convert a 128 kbps MP3 to 256 kbps. The 128 kbps file is copied unchanged because re-encoding it at a higher bitrate cannot restore audio information that was already lost.

## Existing Target Files

Before processing a source file, the script checks whether the corresponding MP3 already exists in the target directory.

If it exists, the source is skipped.

For example:

```text
Source:
D:\Music\Rock\Album\Song.flac

Target:
D:\Converted Music\Rock\Album\Song.mp3
```

If `Song.mp3` already exists:

```text
SKIP
Reason : Target MP3 already exists
```

The script does not:

- Re-convert the source.
- Replace the existing target.
- Modify the existing target.
- Compare bitrate or metadata of the existing target.

**The existence of the target MP3 is enough to skip the source file.**

This makes repeated runs efficient.

## Folder Structure

The source folder hierarchy is preserved.

For example:

```text
D:\Music
├── Rock
│   ├── Album 1
│   │   ├── Track 01.flac
│   │   └── Track 02.mp3
│   └── Album 2
│       └── Track 01.m4a
│
└── Jazz
    └── Album 3
        └── Track 01.wav
```

Output:

```text
D:\Converted Music
├── Rock
│   ├── Album 1
│   │   ├── Track 01.mp3
│   │   └── Track 02.mp3
│   └── Album 2
│       └── Track 01.mp3
│
└── Jazz
    └── Album 3
        └── Track 01.mp3
```

## Metadata and Album Artwork

For files that require conversion, FFmpeg is configured to preserve compatible source metadata.

The script attempts to preserve:

- Title
- Artist
- Album
- Album artist
- Genre
- Track number
- Disc number
- Date/year
- Comments
- Other compatible metadata

Embedded album artwork is also mapped to the output MP3 when available.

The resulting MP3 uses ID3v2.3 metadata for broad compatibility with music players and library applications.

### Metadata limitations

Audio formats use different metadata systems.

For example:

- FLAC commonly uses Vorbis Comments.
- MP3 commonly uses ID3.
- M4A commonly uses MP4/iTunes-style metadata.

Some format-specific or proprietary tags cannot be represented exactly in an MP3 ID3 tag.

Therefore, the script preserves compatible metadata where possible but cannot guarantee that every source-specific tag survives conversion.

The same applies to album artwork. Embedded artwork is preserved where FFmpeg can read and map it, and it may be converted into an MP3-compatible image format.

## Supported Audio Extensions

The current extension list includes:

```text
.mp3
.wav
.flac
.m4a
.aac
.ogg
.oga
.opus
.wma
.alac
.aiff
.aif
.ape
.wv
.mka
.mp2
.amr
.ac3
.dts
.m4b
.webm
```

FFmpeg supports additional audio formats. If your collection contains an extension not listed above, add it to `AUDIO_EXTENSIONS` in `main.py`.

## Logging

Every run writes two separate log files to a `logs` folder inside the **target** directory:

```text
D:\Converted Music
└── logs
    ├── success.log   # copied, converted, and skipped files
    └── errors.log    # failed files and unexpected errors
```

- `success.log` records every file that was **copied**, **converted**, or **skipped** (already existed), along with the reason and relevant bitrate.
- `errors.log` records every file that **failed** to process (FFmpeg errors, copy failures, unexpected exceptions), along with the reason.
- Each run appends a `Run started` marker and a final `SUMMARY` line (files found, copied, converted, skipped, failed) to **both** log files, so history from previous runs is preserved.
- The log file paths are also printed to the console at the end of each run.

## Safety

The source files are never modified.

The script only:

1. Reads source files.
2. Creates directories in the target.
3. Copies qualifying MP3 files.
4. Converts files that require conversion.
5. Skips target files that already exist.

The original music collection remains untouched.

## Re-running the Script

The script is designed to be run multiple times.

Example:

```text
First run:
100 files found
70 converted
20 copied
10 skipped
```

After adding new music:

```text
Second run:
120 files found
20 converted
0 copied
100 skipped
```

Existing target MP3 files are skipped.

## Example Session

```text
======================================================================
RECURSIVE AUDIO -> MP3 CONVERTER
======================================================================

Source Path: D:\Music
Target Path: D:\Converted Music

Select target MP3 bitrate:

  1. 128 kbps
  2. 192 kbps
  3. 256 kbps

Enter choice (1-3): 2

======================================================================
SETTINGS
======================================================================

Source:
  D:\Music

Target:
  D:\Converted Music

MP3 bitrate:
  192 kbps

======================================================================

MP3 FOUND
  File    : D:\Music\Rock\Song A.mp3
  Bitrate : 128 kbps
  Target  : 192 kbps

COPY
  Source : D:\Music\Rock\Song A.mp3
  Target : D:\Converted Music\Rock\Song A.mp3
  Reason : MP3 already meets the selected bitrate
  Mode   : Exact file copy

MP3 FOUND
  File    : D:\Music\Rock\Song B.mp3
  Bitrate : 320 kbps
  Target  : 192 kbps
  Action  : Re-encode 320 kbps -> 192 kbps

CONVERT
  Source : D:\Music\Rock\Song B.mp3
  Target : D:\Converted Music\Rock\Song B.mp3
  Format : MP3 192 kbps
  Tags   : Preserving metadata
  Art    : Preserving embedded album art

SKIP
  Source : D:\Music\Jazz\Song C.flac
  Target : D:\Converted Music\Jazz\Song C.mp3
  Reason : Target MP3 already exists

======================================================================
PROCESSING COMPLETE
======================================================================

Selected bitrate:              192 kbps
Total audio files found:       3
MP3 files copied unchanged:    1
Files converted to MP3:        1
Files skipped:                 1
Failed:                        0

Output directory:
  D:\Converted Music

======================================================================
```

## Project Files

```text
audio-converter/
├── main.py    # Main application
├── README.md             # Documentation
└── requirements.txt      # Python dependencies (none)
```

## License

Add your preferred license here if this project will be distributed publicly.
