import sys
import os
import re
import threading
from collections import Counter

import site
site_user_site = site.getusersitepackages()
if site_user_site not in sys.path:
    sys.path.append(site_user_site)

package_to_module = {
    'boto3': 'boto3',
    'questionary': 'questionary',
    'colorama': 'colorama',
    'tqdm': 'tqdm',
    'rich': 'rich',
    'alive-progress': 'alive_progress',
    'prompt_toolkit': 'prompt_toolkit',
}

def check_and_install_dependencies():
    import subprocess
    missing_packages = []
    for package_name, module_name in package_to_module.items():
        try:
            __import__(module_name)
        except ImportError:
            missing_packages.append(package_name)
    if missing_packages:
        print("The following packages are required to run the script:")
        for pkg in missing_packages:
            print(f"- {pkg}")
        install = input("Do you want to install the missing dependencies? [y/N]: ").strip().lower()
        if install == 'y':
            in_virtualenv = (
                hasattr(sys, 'real_prefix') or
                (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
            )
            for pkg in missing_packages:
                print(f"Installing {pkg}...")
                try:
                    if in_virtualenv:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                    else:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--user"])
                except subprocess.CalledProcessError as e:
                    print(f"Error installing {pkg}: {e}")
                    print("Could not install the dependency. The script cannot continue.")
                    sys.exit(1)
            for pkg in missing_packages:
                module_name = package_to_module[pkg]
                try:
                    globals()[module_name] = __import__(module_name)
                except ImportError as e:
                    print(f"Error importing {module_name} after installation: {e}")
                    print("The script cannot continue.")
                    sys.exit(1)
            print("Dependencies installed successfully. Continuing with the script...")
        else:
            print("Dependencies not installed. The script cannot continue.")
            sys.exit(1)

check_and_install_dependencies()

import boto3
import questionary
from questionary import Choice
import colorama
from colorama import init
from tqdm import tqdm
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.table import Table
from rich import box
from alive_progress import alive_bar

import configparser
from botocore.exceptions import ClientError

init(autoreset=True)
console = Console()

custom_style = Style([
    ('qmark', 'fg:#E91E63 bold'),
    ('answer', 'fg:#2196f3 bold'),
    ('instruction', ''),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#03a9f4 bold'),
    ('selected', 'fg:#f44336 bold'),
    ('separator', 'fg:#cc5454'),
    ('text', ''),
])

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

class ProgressPercentage:
    def __init__(self, client, bucket, key):
        self._client = client
        self._bucket = bucket
        self._key = key
        self._size = self._get_size()
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self._tqdm = tqdm(
            total=self._size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=key,
            leave=True
        )

    def _get_size(self):
        response = self._client.head_object(Bucket=self._bucket, Key=self._key)
        return response['ContentLength']

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            self._tqdm.update(bytes_amount)
            if self._seen_so_far >= self._size:
                self._tqdm.close()

def configure_aws_credentials():
    access_key = questionary.text(
        "Enter your AWS Access Key ID:",
        style=custom_style
    ).ask().strip()
    secret_key = questionary.password(
        "Enter your AWS Secret Access Key:",
        style=custom_style
    ).ask().strip()
    profile_name = 'default'
    aws_credentials_dir = os.path.expanduser('~/.aws')
    aws_credentials_file = os.path.join(aws_credentials_dir, 'credentials')
    if not os.path.exists(aws_credentials_dir):
        os.makedirs(aws_credentials_dir, exist_ok=True)
    config = configparser.ConfigParser()
    if os.path.exists(aws_credentials_file):
        config.read(aws_credentials_file)
    else:
        open(aws_credentials_file, 'a').close()
    if not config.has_section(profile_name):
        config.add_section(profile_name)
    config.set(profile_name, 'aws_access_key_id', access_key)
    config.set(profile_name, 'aws_secret_access_key', secret_key)
    with open(aws_credentials_file, 'w') as configfile:
        config.write(configfile)
    console.print("\n[green]AWS credentials configured successfully![/green]\n")

def validate_bucket_name(bucket_name):
    """
    Validates the S3 bucket name against AWS naming conventions.
    """
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        return False
    pattern = re.compile(r'^(?![0-9]+$)(?!.*\.\.)(?!\-)[a-z0-9\-\.]{3,63}$')
    if not pattern.match(bucket_name):
        return False
    # Additional check to prevent IP-like bucket names
    ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if ip_pattern.match(bucket_name):
        return False
    return True

def check_aws_credentials():
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials or not credentials.access_key or not credentials.secret_key:
            console.print("[red]AWS credentials are not configured.[/red]")
            return False
        sts = session.client('sts')
        sts.get_caller_identity()
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ['InvalidClientTokenId', 'SignatureDoesNotMatch', 'AccessDenied']:
            console.print("[red]Your AWS credentials are invalid or do not have the necessary permissions.[/red]")
            return False
        else:
            console.print(f"[red]An error occurred: {e}[/red]")
            return False
    except Exception as e:
        console.print(f"[red]An error occurred while checking AWS credentials: {e}[/red]")
        return False

def main():
    help_message = """
Usage:
    s3Fetch.py [-h]

Description:
    A tool to explore and download files from S3 buckets in a simplified way.

Features:
    - Connect to a user-specified S3 bucket.
    - List files within the bucket.
    - Filter files by pattern (regex) for precise selection.
    - Display file count by extension.
    - Interactive selection of files for download.
    - Download selected files to a specified directory.
    - Interactive menu to change buckets or exit the tool.

Options:
    -h, --help      Show this help message.
    """

    if '-h' in sys.argv or '--help' in sys.argv:
        print(help_message)
        sys.exit(0)

    ascii_art = r"""
 __ _____   ___    _       _
/ _\___ /  / __\__| |_ ___| |__
\ \  |_ \ / _\/ _ \ __/ __| '_ \
_\ \___) / / |  __/ || (__| | | |
\__/____/\/   \___|\__\___|_| |_|

by @david_v4l3n
https://github.com/david-valen
"""
    console.print(f"[bold green]{ascii_art}[/bold green]")
    title = "Simplified exploration and download of S3 Buckets"
    decor = "=" * len(title)
    console.print(f"[cyan bold]{decor}[/cyan bold]")
    console.print(f"[cyan bold]{title}[/cyan bold]")
    console.print(f"[cyan bold]{decor}[/cyan bold]")

    while True:
        credentials_valid = check_aws_credentials()
        if not credentials_valid:
            configure_choice = questionary.select(
                "AWS credentials are not configured or invalid. What would you like to do?",
                choices=[
                    Choice('Configure AWS credentials', value='configure'),
                    Choice('Exit', value='exit')
                ],
                style=custom_style
            ).ask()
            if configure_choice == 'configure':
                configure_aws_credentials()
            else:
                console.print("\n[cyan]Exiting the tool. Goodbye![/cyan]")
                sys.exit(0)
        else:
            break

    files = []
    bucket_name = None
    bucket_history = InMemoryHistory()
    try:
        while True:
            if not bucket_name:
                clear_screen()
                console.print(f"[bold green]{ascii_art}[/bold green]")
                console.print(f"[cyan bold]{decor}[/cyan bold]")
                console.print(f"[cyan bold]{title}[/cyan bold]")
                console.print(f"[cyan bold]{decor}[/cyan bold]")
                try:
                    bucket_name = questionary.text(
                        "Enter the bucket name:",
                        history=bucket_history,
                        style=custom_style
                    ).ask()
                    if bucket_name:
                        if not validate_bucket_name(bucket_name):
                            console.print("[red]Invalid bucket name. Please enter a valid S3 bucket name.[/red]")
                            bucket_name = None
                            input("\nPress Enter to continue...")
                            continue
                        if bucket_name not in bucket_history.get_strings():
                            bucket_history.append_string(bucket_name)
                    else:
                        console.print()
                        exit_choice = questionary.confirm("Do you want to exit the tool?").ask()
                        if exit_choice:
                            console.print("\n[cyan]Exiting the tool. Goodbye![/cyan]")
                            sys.exit(0)
                        else:
                            continue
                except KeyboardInterrupt:
                    console.print()
                    exit_choice = questionary.confirm("Do you want to exit the tool?").ask()
                    if exit_choice:
                        console.print("\n[cyan]Exiting the tool. Goodbye![/cyan]")
                        sys.exit(0)
                    else:
                        continue

                s3 = boto3.client('s3')

                try:
                    s3.head_bucket(Bucket=bucket_name)
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    status_code = e.response['ResponseMetadata']['HTTPStatusCode']
                    if status_code == 404 or error_code == 'NoSuchBucket':
                        console.print(f"[red]The bucket '{bucket_name}' does not exist.[/red]")
                    elif status_code == 403 or error_code == 'AccessDenied':
                        console.print(f"[red]You do not have access to the bucket '{bucket_name}'.[/red]")
                    else:
                        console.print(f"[red]Error accessing bucket '{bucket_name}': {e}[/red]")
                    bucket_name = None
                    input("\nPress Enter to continue...")
                    continue

                files = []

                paginator = s3.get_paginator('list_objects_v2')
                try:
                    console.print("\n[green]Listing files in the bucket...[/green]")
                    pages = paginator.paginate(Bucket=bucket_name)

                    with alive_bar(bar='bubbles') as bar:
                        for page in pages:
                            if 'Contents' in page:
                                files_in_page = [obj['Key'] for obj in page['Contents'] if not obj['Key'].endswith('/')]
                                files.extend(files_in_page)
                            bar()
                    if not files:
                        console.print(
                            f"[red]The bucket '{bucket_name}' contains no files.[/red]"
                        )
                        bucket_name = None
                        input("\nPress Enter to continue...")
                        continue
                except ClientError as e:
                    console.print(f"[red]An error occurred while listing the bucket contents: {e}[/red]")
                    bucket_name = None
                    input("\nPress Enter to continue...")
                    continue
                except Exception as e:
                    console.print(
                        f"[red]Error accessing bucket '{bucket_name}': {e}[/red]"
                    )
                    bucket_name = None
                    input("\nPress Enter to continue...")
                    continue

                console.print(
                    f"\n[green]Total files found: {len(files)}[/green]"
                )

                extensions = [
                    os.path.splitext(f)[1].lower() for f in files if os.path.splitext(f)[1]
                ]

                ext_counts = Counter(extensions)

                sorted_ext_counts = sorted(
                    ext_counts.items(), key=lambda x: x[1], reverse=True
                )

                table = Table(box=box.SIMPLE_HEAVY)
                table.add_column("Extension", justify="left", style="cyan", no_wrap=True)
                table.add_column("Count", justify="right", style="magenta")
                for ext, count in sorted_ext_counts:
                    table.add_row(ext, str(count))

            current_files = files.copy()

            while True:
                clear_screen()
                console.print(f"[bold green]{ascii_art}[/bold green]")
                console.print(f"[cyan bold]{decor}[/cyan bold]")
                console.print(f"[cyan bold]{title}[/cyan bold]")
                console.print(f"[cyan bold]{decor}[/cyan bold]")

                console.print(table)

                console.print(
                    f"\n[green]Total current files: {len(current_files)}[/green]"
                )

                try:
                    action_choice = questionary.select(
                        "What would you like to do?",
                        choices=[
                            Choice('View all files', value='view_all'),
                            Choice('Filter files', value='filter'),
                            Choice('Change bucket', value='change'),
                            Choice('Exit', value='exit')
                        ],
                        style=custom_style
                    ).ask()
                except KeyboardInterrupt:
                    console.print()
                    exit_choice = questionary.confirm("Do you want to exit the tool?").ask()
                    if exit_choice:
                        console.print("\n[cyan]Exiting the tool. Goodbye![/cyan]")
                        sys.exit(0)
                    else:
                        continue

                if action_choice == 'change':
                    bucket_name = None
                    break
                if action_choice == 'exit':
                    console.print("\n[cyan]Exiting the tool. Goodbye![/cyan]")
                    sys.exit(0)
                if action_choice == 'view_all':
                    pass  # Proceed with current_files as is
                if action_choice == 'filter':
                    while True:
                        clear_screen()
                        console.print(f"[bold green]{ascii_art}[/bold green]")
                        console.print(f"[cyan bold]{decor}[/cyan bold]")
                        console.print(f"[cyan bold]{title}[/cyan bold]")
                        console.print(f"[cyan bold]{decor}[/cyan bold]")
                        console.print(table)
                        pattern = console.input(
                            "[yellow]Enter a search pattern "
                            "(regex, e.g., '.*\\.txt$' for .txt files): [/yellow]"
                        ).strip()
                        if not pattern:
                            console.print("[red]You must enter a valid pattern from the extension list.[/red]")
                            input("\nPress Enter to continue...")
                            continue
                        try:
                            regex = re.compile(pattern)
                            filtered_files = list(filter(regex.search, files))
                            if not filtered_files:
                                console.print(
                                    "[red]No files found matching the provided pattern.[/red]"
                                )
                                retry = questionary.confirm(
                                    "Do you want to enter another pattern?"
                                ).ask()
                                if retry:
                                    continue
                                else:
                                    filtered_files = files.copy()
                                    break
                            else:
                                current_files = filtered_files
                                console.print(
                                    f"\n[green]Files found after filtering: "
                                    f"{len(current_files)}[/green]"
                                )
                                break
                        except re.error as e:
                            console.print(f"[red]Invalid pattern: {e}[/red]")
                            retry = questionary.confirm(
                                "Do you want to enter another pattern?"
                            ).ask()
                            if retry:
                                continue
                            else:
                                break

                    if not current_files:
                        console.print("[red]No files to display.[/red]")
                        continue

                while True:
                    max_choices = 50
                    display_files = current_files
                    if len(display_files) > max_choices:
                        console.print(
                            f"[yellow]There are more than {max_choices} files to select. "
                            f"Only the first {max_choices} files will be displayed.[/yellow]"
                        )
                        display_files = display_files[:max_choices]

                    clear_screen()
                    console.print(f"[bold green]{ascii_art}[/bold green]")
                    console.print(f"[cyan bold]{decor}[/cyan bold]")
                    console.print(f"[cyan bold]{title}[/cyan bold]")
                    console.print(f"[cyan bold]{decor}[/cyan bold]")

                    console.print("\n[cyan]Select the files to download:[/cyan]")
                    console.print("[yellow](Use arrow keys to navigate, <space> to select, enter to confirm. Press 'Ctrl+C' to exit)[/yellow]")
                    try:
                        selected_files = questionary.checkbox(
                            "Press space to select, enter to confirm",
                            choices=display_files,
                            instruction="(Use arrow keys to navigate, <space> to select, <a> to select all, <i> to invert selection)",
                            style=custom_style
                        ).ask()
                    except KeyboardInterrupt:
                        console.print()
                        exit_choice = questionary.confirm("Do you want to exit the tool?").ask()
                        if exit_choice:
                            console.print("\n[cyan]Exiting the tool. Goodbye![/cyan]")
                            sys.exit(0)
                        else:
                            continue

                    if not selected_files:
                        console.print("[yellow]No files have been selected.[/yellow]")
                        back_choice = questionary.select(
                            "No files selected. What would you like to do?",
                            choices=[
                                Choice('Select files again', value='select'),
                                Choice('Return to previous menu', value='menu'),
                                Choice('Exit', value='exit')
                            ],
                            style=custom_style
                        ).ask()
                        if back_choice == 'select':
                            continue
                        elif back_choice == 'menu':
                            break
                        else:
                            console.print("\n[cyan]Exiting the tool. Goodbye![/cyan]")
                            sys.exit(0)
                    else:
                        break

                if selected_files:
                    save_choice = questionary.confirm(
                        "Do you want to save the files to a specific directory?"
                    ).ask()

                    if save_choice:
                        download_dir = questionary.path(
                            "Enter the directory where you want to save the files:",
                            only_directories=True,
                            style=custom_style
                        ).ask()
                        if not download_dir:
                            console.print("[red]Invalid directory. Using default directory.[/red]")
                            download_dir = os.path.abspath(bucket_name)
                        else:
                            download_dir = os.path.abspath(download_dir)
                    else:
                        download_dir = os.path.abspath(bucket_name)

                    if not os.path.exists(download_dir):
                        os.makedirs(download_dir, exist_ok=True)

                    console.print("\n[green]Starting download of selected files...[/green]")
                    for file_key in selected_files:
                        local_path = os.path.normpath(os.path.join(download_dir, file_key))
                        local_dir = os.path.dirname(local_path)
                        if not os.path.exists(local_dir):
                            os.makedirs(local_dir, exist_ok=True)
                        try:
                            s3.download_file(
                                bucket_name,
                                file_key,
                                local_path,
                                Callback=ProgressPercentage(s3, bucket_name, file_key)
                            )
                        except Exception as e:
                            console.print(
                                f"\n[red]Error downloading {file_key}: {e}[/red]"
                            )

                    console.print()
                    repeat = questionary.select(
                        "What would you like to do now?",
                        choices=[
                            Choice('Download more files', value='continue'),
                            Choice('Change bucket', value='change'),
                            Choice('Exit', value='exit')
                        ],
                        style=custom_style
                    ).ask()

                    if repeat == 'continue':
                        current_files = files.copy()
                        continue
                    elif repeat == 'change':
                        bucket_name = None
                        break
                    else:
                        console.print("\n[cyan]Exiting the tool. Goodbye![/cyan]")
                        sys.exit(0)
    except KeyboardInterrupt:
        console.print()
        exit_choice = questionary.confirm("Do you want to exit the tool?").ask()
        if exit_choice:
            console.print("\n[cyan]Exiting the tool. Goodbye![/cyan]")
            sys.exit(0)
        else:
            main()

if __name__ == "__main__":
    main()
