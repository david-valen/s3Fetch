# S3Fetch AWS

[![Python](https://img.shields.io/badge/Python-3.6%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Command-line tool for exploring and downloading files from Amazon S3 buckets with ease.

## 🛠 Features

- **Automated dependency management**: Installs required packages if missing, reducing setup time.
- **S3 bucket navigation**: Connects to specified S3 buckets, listing files by extensions and counts.
- **Pattern-based filtering**: Allows filtering by regular expressions, making file selection precise.
- **Interactive selection and download**: Enables multi-file selection for downloads, with a progress tracker.
- **Custom download directory**: Choose a specific download path, or use the bucket name as the default directory.

### Prerequisites

- **Python 3.6+** is required. Install it from [Python.org](https://www.python.org/).
- **AWS Credentials**: Configure through `~/.aws/credentials` or set up environment variables for access.

### Installation

1. Clone this repository:

    ```bash
    git clone https://github.com/david-valen/S3Fetch.git
    cd S3Fetch
    ```

2. Run the tool. It will check and install missing dependencies as needed.

    ```bash
    python s3Fetch.py
    ```

## 📝 How It Works

1. Launching the tool: The script starts by checking dependencies, installing any missing packages.
2. Bucket selection: Prompts the user to enter an S3 bucket name. After connection, it lists files in the bucket by extension.
3. Filtering files: Filter files with regex patterns to locate specific types or names.
4. File selection and download: Select files interactively for download. You can choose a custom directory or the default.

## 📌 Example Workflow

1. Run the tool:

    ```bash
    python s3Fetch.py
    ```
2. Enter the S3 bucket name when prompted.
3. Apply a regex pattern to filter files (optional).
4. Select files for download.
5. Specify a download directory or use the default.
6. Track download progress in real time.

## 📋 Dependencies

This tool requires the following Python packages:

- boto3
- questionary
- colorama
- tqdm
- rich
- alive_progress
- prompt_toolkit

If any dependencies are missing, the tool will prompt you to install them upon first run.
