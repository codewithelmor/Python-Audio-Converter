import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


# =========================================================
# Configuration
# =========================================================

AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".flac",
    ".m4a",
    ".aac",
    ".ogg",
    ".oga",
    ".opus",
    ".wma",
    ".alac",
    ".aiff",
    ".aif",
    ".ape",
    ".wv",
    ".mka",
    ".mp2",
    ".amr",
    ".ac3",
    ".dts",
    ".m4b",
    ".webm",
}

ALLOWED_BITRATES = {
    "1": 128,
    "2": 192,
    "3": 256,
}


# =========================================================
# Logging
# =========================================================

def setup_loggers(target_root):
    """
    Create two separate log files inside the target directory:

        logs/success.log  -> copied / converted / skipped files
        logs/errors.log    -> failed files and unexpected errors

    Each logger writes only to its own file (propagate is
    disabled so messages never leak into the other log or
    the console).
    """

    logs_dir = target_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatter = logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S")

    # ---- Success logger --------------------------------------------------
    success_logger = logging.getLogger("audio_converter.success")
    success_logger.setLevel(logging.INFO)
    success_logger.propagate = False
    if not success_logger.handlers:
        success_handler = logging.FileHandler(
            logs_dir / "success.log", encoding="utf-8"
        )
        success_handler.setFormatter(formatter)
        success_logger.addHandler(success_handler)

    # ---- Error logger ------------------------------------------------------
    error_logger = logging.getLogger("audio_converter.errors")
    error_logger.setLevel(logging.INFO)
    error_logger.propagate = False
    if not error_logger.handlers:
        error_handler = logging.FileHandler(
            logs_dir / "errors.log", encoding="utf-8"
        )
        error_handler.setFormatter(formatter)
        error_logger.addHandler(error_handler)

    success_logger.info("=" * 70)
    success_logger.info(f"Run started {timestamp}")
    success_logger.info("=" * 70)

    error_logger.info("=" * 70)
    error_logger.info(f"Run started {timestamp}")
    error_logger.info("=" * 70)

    return success_logger, error_logger


# =========================================================
# FFmpeg checks
# =========================================================

def check_ffmpeg():
    """Check whether FFmpeg and FFprobe are installed."""

    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        subprocess.run(
            ["ffprobe", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        return True

    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


# =========================================================
# Get MP3 bitrate
# =========================================================

def get_mp3_bitrate(file_path):
    """
    Get the bitrate of an MP3 using ffprobe.

    Returns:
        int: bitrate in kbps
        None: if bitrate could not be determined
    """

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=bit_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

        bitrate = result.stdout.strip()

        if bitrate:
            return int(bitrate) // 1000

    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        ValueError,
    ):
        pass

    return None


# =========================================================
# Convert to MP3
# =========================================================

def convert_to_mp3(source, target, target_bitrate):
    """
    Convert an audio file to MP3 at the selected bitrate.

    Attempts to preserve:
        - Audio metadata
        - ID3 tags
        - Artist
        - Album
        - Album artist
        - Title
        - Genre
        - Track number
        - Disc number
        - Date/year
        - Comments
        - Embedded album artwork
    """

    target.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",

        # Input
        "-i", str(source),

        # -------------------------------------------------
        # Audio
        # -------------------------------------------------

        "-map", "0:a:0",
        "-c:a", "libmp3lame",
        "-b:a", f"{target_bitrate}k",

        # -------------------------------------------------
        # Metadata
        # -------------------------------------------------

        "-map_metadata", "0",

        # -------------------------------------------------
        # Album artwork
        # -------------------------------------------------

        # Map embedded artwork when available.
        "-map", "0:v:0?",

        # MP3-compatible artwork encoding.
        "-c:v", "mjpeg",

        # Mark artwork as attached picture.
        "-disposition:v", "attached_pic",

        # -------------------------------------------------
        # MP3 metadata compatibility
        # -------------------------------------------------

        "-id3v2_version", "3",
        "-write_id3v1", "1",

        # Output
        str(target),
    ]

    print()
    print("CONVERT")
    print(f"  Source : {source}")
    print(f"  Target : {target}")
    print(f"  Format : MP3 {target_bitrate} kbps")
    print("  Tags   : Preserving metadata")
    print("  Art    : Preserving embedded album art")

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        print()
        print("ERROR: FFmpeg conversion failed.")
        print(f"File: {source}")
        print()
        print(result.stderr)

        # Remove incomplete output if one was created.
        if target.exists():
            try:
                target.unlink()
            except OSError:
                pass

        return False

    return True


# =========================================================
# Copy MP3
# =========================================================

def copy_mp3(source, target):
    """
    Copy an MP3 without modifying it.

    This preserves the original file exactly, including:
        - Audio
        - Album artwork
        - ID3 tags
        - Other metadata
    """

    target.parent.mkdir(parents=True, exist_ok=True)

    print()
    print("COPY")
    print(f"  Source : {source}")
    print(f"  Target : {target}")
    print("  Reason : MP3 already meets the selected bitrate")
    print("  Mode   : Exact file copy")

    shutil.copy2(source, target)

    return True


# =========================================================
# Process one file
# =========================================================

def process_file(
    source_file,
    source_root,
    target_root,
    target_bitrate,
    success_logger,
    error_logger,
):
    """
    Process one audio file while preserving its directory
    structure.
    """

    relative_path = source_file.relative_to(source_root)

    # MP3 keeps its filename.
    # Non-MP3 files receive an .mp3 extension.
    if source_file.suffix.lower() == ".mp3":
        target_file = target_root / relative_path
    else:
        target_file = target_root / relative_path.with_suffix(".mp3")

    # -----------------------------------------------------
    # Skip existing target
    # -----------------------------------------------------

    if target_file.exists():

        print()
        print("SKIP")
        print(f"  Source : {source_file}")
        print(f"  Target : {target_file}")
        print("  Reason : Target MP3 already exists")

        success_logger.info(
            f"SKIP | source={source_file} | target={target_file} "
            f"| reason=Target MP3 already exists"
        )

        return "skipped"

    # -----------------------------------------------------
    # MP3
    # -----------------------------------------------------

    if source_file.suffix.lower() == ".mp3":

        bitrate = get_mp3_bitrate(source_file)

        # If bitrate cannot be determined, convert it.
        if bitrate is None:

            print()
            print("WARNING")
            print(f"  Could not determine bitrate:")
            print(f"  {source_file}")
            print(f"  Converting to {target_bitrate} kbps.")

            if convert_to_mp3(
                source_file,
                target_file,
                target_bitrate,
            ):
                success_logger.info(
                    f"CONVERT | source={source_file} | target={target_file} "
                    f"| reason=Bitrate could not be determined "
                    f"| bitrate={target_bitrate}kbps"
                )
                return "converted"

            error_logger.info(
                f"FAILED | source={source_file} | target={target_file} "
                f"| reason=Conversion failed (unknown source bitrate) "
                f"| bitrate={target_bitrate}kbps"
            )
            return "failed"

        print()
        print("MP3 FOUND")
        print(f"  File    : {source_file}")
        print(f"  Bitrate : {bitrate} kbps")
        print(f"  Target  : {target_bitrate} kbps")

        # -------------------------------------------------
        # Existing MP3 is at or below selected bitrate.
        #
        # Example:
        # Selected = 192
        # Source   = 128
        #
        # Copy unchanged.
        # -------------------------------------------------

        if bitrate <= target_bitrate:

            if copy_mp3(source_file, target_file):
                success_logger.info(
                    f"COPY | source={source_file} | target={target_file} "
                    f"| reason=MP3 already at or below {target_bitrate}kbps "
                    f"| source_bitrate={bitrate}kbps"
                )
                return "copied"

            error_logger.info(
                f"FAILED | source={source_file} | target={target_file} "
                f"| reason=Copy failed "
                f"| source_bitrate={bitrate}kbps"
            )
            return "failed"

        # -------------------------------------------------
        # Existing MP3 is above selected bitrate.
        #
        # Example:
        # Selected = 192
        # Source   = 320
        #
        # Re-encode to selected bitrate.
        # -------------------------------------------------

        print(
            f"  Action  : Re-encode "
            f"{bitrate} kbps -> {target_bitrate} kbps"
        )

        if convert_to_mp3(
            source_file,
            target_file,
            target_bitrate,
        ):
            success_logger.info(
                f"CONVERT | source={source_file} | target={target_file} "
                f"| reason=Re-encode {bitrate}kbps -> {target_bitrate}kbps"
            )
            return "converted"

        error_logger.info(
            f"FAILED | source={source_file} | target={target_file} "
            f"| reason=Re-encode failed "
            f"| source_bitrate={bitrate}kbps -> {target_bitrate}kbps"
        )
        return "failed"

    # -----------------------------------------------------
    # Non-MP3 audio
    # -----------------------------------------------------

    print()
    print("NON-MP3 AUDIO")
    print(f"  Source : {source_file}")
    print(f"  Target : {target_file}")

    if convert_to_mp3(
        source_file,
        target_file,
        target_bitrate,
    ):
        success_logger.info(
            f"CONVERT | source={source_file} | target={target_file} "
            f"| reason=Non-MP3 converted to {target_bitrate}kbps"
        )
        return "converted"

    error_logger.info(
        f"FAILED | source={source_file} | target={target_file} "
        f"| reason=Non-MP3 conversion failed "
        f"| target_bitrate={target_bitrate}kbps"
    )
    return "failed"


# =========================================================
# Scan source directory
# =========================================================

def process_directory(source_path, target_path, target_bitrate):

    source_root = Path(source_path).resolve()
    target_root = Path(target_path).resolve()

    # -----------------------------------------------------
    # Validate source
    # -----------------------------------------------------

    if not source_root.exists():
        print()
        print("ERROR: Source path does not exist.")
        return

    if not source_root.is_dir():
        print()
        print("ERROR: Source path is not a directory.")
        return

    # -----------------------------------------------------
    # Prevent source == target
    # -----------------------------------------------------

    if source_root == target_root:
        print()
        print("ERROR:")
        print("Source and Target paths must be different.")
        return

    # -----------------------------------------------------
    # Create target
    # -----------------------------------------------------

    target_root.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------
    # Logging
    # -----------------------------------------------------

    success_logger, error_logger = setup_loggers(target_root)

    # -----------------------------------------------------
    # Statistics
    # -----------------------------------------------------

    total_audio = 0
    total_skipped = 0
    total_mp3_copied = 0
    total_converted = 0
    total_failed = 0

    # -----------------------------------------------------
    # Scan recursively
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("SCANNING SOURCE DIRECTORY")
    print("=" * 70)

    print(f"Source:")
    print(f"  {source_root}")

    print()
    print(f"Target:")
    print(f"  {target_root}")

    print()
    print(f"Selected bitrate:")
    print(f"  {target_bitrate} kbps")

    print("=" * 70)

    for file_path in source_root.rglob("*"):

        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue

        total_audio += 1

        try:

            result = process_file(
                file_path,
                source_root,
                target_root,
                target_bitrate,
                success_logger,
                error_logger,
            )

            if result == "skipped":
                total_skipped += 1

            elif result == "copied":
                total_mp3_copied += 1

            elif result == "converted":
                total_converted += 1

            elif result == "failed":
                total_failed += 1

        except Exception as e:

            print()
            print("=" * 70)
            print("UNEXPECTED ERROR")
            print("=" * 70)

            print(f"File:")
            print(f"  {file_path}")

            print()
            print("Error:")
            print(f"  {e}")

            print("=" * 70)

            error_logger.info(
                f"FAILED | source={file_path} | target=N/A "
                f"| reason=Unexpected error: {e}"
            )

            total_failed += 1

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print()
    print()
    print("=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)

    print(f"Selected bitrate:              {target_bitrate} kbps")
    print(f"Total audio files found:       {total_audio}")
    print(f"MP3 files copied unchanged:    {total_mp3_copied}")
    print(f"Files converted to MP3:        {total_converted}")
    print(f"Files skipped:                  {total_skipped}")
    print(f"Failed:                         {total_failed}")

    print()
    print("Output directory:")
    print(f"  {target_root}")

    logs_dir = target_root / "logs"

    print()
    print("Log files:")
    print(f"  {logs_dir / 'success.log'}")
    print(f"  {logs_dir / 'errors.log'}")

    print("=" * 70)

    summary = (
        f"SUMMARY | bitrate={target_bitrate}kbps | found={total_audio} "
        f"| copied={total_mp3_copied} | converted={total_converted} "
        f"| skipped={total_skipped} | failed={total_failed}"
    )
    success_logger.info(summary)
    error_logger.info(summary)


# =========================================================
# Ask for bitrate
# =========================================================

def choose_bitrate():
    """
    Ask the user to select 128, 192, or 256 kbps.
    """

    print()
    print("Select target MP3 bitrate:")
    print()
    print("  1. 128 kbps")
    print("  2. 192 kbps")
    print("  3. 256 kbps")
    print()

    while True:

        choice = input("Enter choice (1-3): ").strip()

        if choice in ALLOWED_BITRATES:
            return ALLOWED_BITRATES[choice]

        print()
        print("Invalid choice.")
        print("Please enter 1, 2, or 3.")
        print()


# =========================================================
# Main
# =========================================================

def main():

    print()
    print("=" * 70)
    print("RECURSIVE AUDIO -> MP3 CONVERTER")
    print("=" * 70)
    print()

    # -----------------------------------------------------
    # Check FFmpeg
    # -----------------------------------------------------

    if not check_ffmpeg():

        print("ERROR: FFmpeg was not found.")
        print()
        print(
            "Please install FFmpeg and make sure both "
            "ffmpeg.exe and ffprobe.exe are available in PATH."
        )
        print()

        input("Press Enter to exit...")
        return

    # -----------------------------------------------------
    # Ask for source path
    # -----------------------------------------------------

    source_path = input("Source Path: ").strip().strip('"')

    # -----------------------------------------------------
    # Ask for target path
    # -----------------------------------------------------

    target_path = input("Target Path: ").strip().strip('"')

    # -----------------------------------------------------
    # Validate paths
    # -----------------------------------------------------

    if not source_path:

        print()
        print("ERROR: Source path is required.")
        return

    if not target_path:

        print()
        print("ERROR: Target path is required.")
        return

    # -----------------------------------------------------
    # Ask for bitrate
    # -----------------------------------------------------

    target_bitrate = choose_bitrate()

    # -----------------------------------------------------
    # Start processing
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("SETTINGS")
    print("=" * 70)

    print(f"Source:")
    print(f"  {source_path}")

    print()
    print(f"Target:")
    print(f"  {target_path}")

    print()
    print(f"MP3 bitrate:")
    print(f"  {target_bitrate} kbps")

    print("=" * 70)

    process_directory(
        source_path,
        target_path,
        target_bitrate,
    )

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
