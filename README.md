# S3Fetch AWS

[![Python](https://img.shields.io/badge/Python-3.6%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Tired of constantly checking AWS cheatsheets just to list an S3 bucket or download files stored in it? I was too!😮‍💨

Command-line tool for exploring and downloading files from Amazon S3 buckets with an interactive user experience.

### Prerequisites

- **Python 3.6+** is required. Install it from [Python.org](https://www.python.org/).
- **AWS Credentials**: Configure through `~/.aws/credentials` or set up environment variables for access. The tool also includes an option to configure credentials directly.

### Installation

1. Clone this repository:

    ```bash
    git clone https://github.com/david-valen/s3Fetch.git
    cd s3Fetch
    ```

2. Run the tool. It will check and install missing dependencies as needed.

    ```bash
    python3 s3Fetch.py
    ```

## 📝 How it works

1. **Dependency check**: The tool begins by checking for all required dependencies and prompts the user to install any missing packages.
2. **AWS credential validation**: Ensures valid AWS credentials are configured. If they are missing or incorrect, the tool prompts the user to configure them interactively.
3. **Bucket access and file listing**: Prompts the user to enter an S3 bucket name. After connecting, it lists all files in the bucket, organized by file extensions with counts for each type.
4. **File filtering**: Allows the user to apply regex patterns to filter files based on extensions or names.
5. **Interactive file selection**: The user can navigate through files, select multiple files for download, or apply additional filters as needed.
6. **File download**: Downloads selected files to a custom or default directory with real-time progress tracking.
7. **Repeat options**: Once files are downloaded, the tool provides options to download more files, change buckets, or exit.

## 📌 Example workflow

![s3Fetch Demo](s3Fetch\assets\s3Fetch.gif)

## 📋 Dependencies

This tool requires the following Python packages:

- `boto3`: AWS SDK for Python, enables access to S3 services.
- `questionary`: Provides interactive command-line interfaces.
- `colorama`: Adds color to terminal text.
- `tqdm`: Displays progress bars for file downloads.
- `rich`: Creates formatted tables for file extension counts.
- `alive-progress`: Adds an animated progress bar during file listing.
- `prompt_toolkit`: Manages input history and styling for interactive prompts.

The tool will prompt you to install any missing dependencies upon the first run.

## ⚠️ Error handling and messages

The tool provides the following error handling mechanisms:

- **Invalid bucket names**: Checks S3 bucket names against AWS naming conventions and alerts the user if the name is invalid.
- **Connection errors**: Displays error messages if the bucket is not accessible due to permissions or if it does not exist.
- **Credential errors**: Checks for valid credentials and provides guidance if they are missing or incorrect, including options to configure them interactively.

## 🔧 Command-line options

Run the tool with the `-h` or `--help` flag for a description of options:

```bash
python3 s3Fetch.py -h