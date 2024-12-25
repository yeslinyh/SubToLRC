import re
import os

# Function to convert ASS subtitle lines to LRC format
def convert_ass_to_lrc(ass_lines):
    lrc_lines = []
    for line in ass_lines:
        match = re.match(r"Dialogue: \d,([\d:.]+),[\d:.]+,.*?,,\d,\d,\d,,(.+)", line)
        if match:
            time_ass = match.group(1)  # Start time in ASS format
            text = match.group(2).strip()  # Subtitle text

            # Convert ASS time (h:mm:ss.cs) to LRC time (mm:ss.cs)
            h, m, s = map(float, time_ass.split(':'))
            total_seconds = h * 3600 + m * 60 + s
            minutes = int(total_seconds // 60)
            seconds = total_seconds % 60
            time_lrc = f"[{minutes:02}:{seconds:05.2f}]"

            # Append to LRC lines
            lrc_lines.append(f"{time_lrc}{text}")

    return "\n".join(lrc_lines)

# Function to convert SRT subtitle lines to LRC format
def convert_srt_to_lrc(srt_lines):
    lrc_lines = []
    for line in srt_lines:
        # Match the time format in SRT
        match = re.match(r"(\d{2}):(\d{2}):(\d{2}),\d{3} --> \d{2}:\d{2}:\d{2},\d{3}", line)
        if match:
            h, m, s = map(int, match.groups())
            total_seconds = h * 3600 + m * 60 + s
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            time_lrc = f"[{minutes:02}:{seconds:05.2f}]"
            lrc_lines.append(time_lrc)
        elif line.strip() and not line.isdigit():
            if lrc_lines:
                lrc_lines[-1] += line.strip()
            else:
                print(f"Warning: Found text without time stamp: {line.strip()}")

    return "\n".join(lrc_lines)

# Function to shift LRC timestamps by a given number of seconds
def shift_lrc_time(lrc_content, shift_seconds):
    shifted_lines = []
    for line in lrc_content.split('\n'):
        match = re.match(r"\[(\d+):(\d+\.\d+)\](.+)", line)
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            text = match.group(3)

            # Calculate total seconds and apply shift
            total_seconds = minutes * 60 + seconds - shift_seconds

            # Prevent negative time values
            if total_seconds < 0:
                total_seconds = 0

            new_minutes = int(total_seconds // 60)
            new_seconds = total_seconds % 60
            new_time = f"[{new_minutes:02}:{new_seconds:05.2f}]"

            # Append shifted line
            shifted_lines.append(f"{new_time}{text}")
        else:
            shifted_lines.append(line)  # Non-timestamp lines remain unchanged

    return "\n".join(shifted_lines)

# Function to read subtitle file and return lines
def read_subtitle_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.readlines()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []

# Function to write LRC content to a file
def write_lrc_file(file_path, content):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
    except Exception as e:
        print(f"Error writing to file {file_path}: {e}")

# Function to extract metadata from the file path
def extract_metadata(file_path):
    # Get the directories and file name from the path
    path_parts = os.path.normpath(file_path).split(os.sep)
    file_name = path_parts[-1].rsplit('.', 1)[0]
    album = path_parts[-2]

    # Remove the artist part from the album if it contains " - "
    if ' - ' in album:
        album = album.split(' - ', 1)[1]

    # Split the file name to get artist and title
    if ' - ' in file_name:
        artist, title = file_name.split(' - ', 1)
    else:
        raise ValueError(f"File name '{file_name}' does not match the expected format 'Artist - Title.ext'")
    
    return artist, title, album

# Function to calculate time shift based on the first line of ASS file and manual offset
def calculate_time_shift(first_line, manual_offset):
    match = re.match(r"Dialogue: \d,([\d:.]+),", first_line)
    if match:
        time_ass = match.group(1)
        h, m, s = map(float, time_ass.split(':'))
        total_seconds = h * 3600 + m * 60 + s
        return total_seconds - manual_offset
    else:
        raise ValueError("The first line does not match the expected format.")

# Function to process subtitle file (ASS or SRT) to LRC and apply time shift
def process_subtitle_file(subtitle_file, manual_offset):
    # Read subtitle file
    subtitle_lines = read_subtitle_file(subtitle_file)
    if not subtitle_lines:
        return

    print(f"Read {len(subtitle_lines)} lines from subtitle file: {subtitle_file}")

    # Determine file type and convert to LRC
    if subtitle_file.endswith('.ass'):
        try:
            time_shift = calculate_time_shift(subtitle_lines[0], manual_offset)
        except ValueError as e:
            print(e)
            return

        print(f"Calculated time shift: {time_shift} seconds")

        lrc_content = convert_ass_to_lrc(subtitle_lines)
    elif subtitle_file.endswith('.srt'):
        time_shift = manual_offset  # For SRT, we don't calculate time shift from the content
        lrc_content = convert_srt_to_lrc(subtitle_lines)
    else:
        print(f"Unsupported file type: {subtitle_file}")
        return

    print("Converted subtitle to LRC:")
    print(lrc_content)

    # Apply time shift
    shifted_lrc_content = shift_lrc_time(lrc_content, time_shift)
    print(f"Shifted LRC content by {time_shift} seconds:")
    print(shifted_lrc_content)

    # Extract metadata
    try:
        artist, title, album = extract_metadata(subtitle_file)
    except ValueError as e:
        print(e)
        return

    # Add metadata to the beginning of the LRC content
    metadata = f"[ti:{title}]\n[ar:{artist}]\n[al:{album}]\n[by:convert-lrc]\n[00:00.00]{artist} - {title}\n"
    final_lrc_content = metadata + shifted_lrc_content

    # Generate LRC file path
    lrc_file = os.path.splitext(subtitle_file)[0] + ".lrc"

    # Write LRC content to file
    write_lrc_file(lrc_file, final_lrc_content)
    print(f"LRC file saved to: {lrc_file}")

# Function to find all .ass and .srt files in the current directory and process them
def find_and_process_subtitle_files(manual_offset):
    # Get the current directory
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    # Traverse the directory tree
    for root, dirs, files in os.walk(current_dir):
        for file in files:
            if file.endswith('.ass') or file.endswith('.srt'):
                subtitle_file_path = os.path.join(root, file)
                print(f"Processing file: {subtitle_file_path}")
                process_subtitle_file(subtitle_file_path, manual_offset)

# Example usage
if __name__ == "__main__":
    # Set manual offset in seconds
    manual_offset = 1

    # Find and process all .ass and .srt files in the current directory and subdirectories
    find_and_process_subtitle_files(manual_offset)