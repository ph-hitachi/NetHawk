import logging
import subprocess
from rich.console import Console

console = Console()

def read_hosts_file():
    try:
        # Try reading normally
        with open('/etc/hosts', 'r') as f:
            return f.read()
    except PermissionError:
        console.print("[[yellow bold]WRN[/]] No permission to read /etc/hosts directly. Trying with sudo...")
        # If normal read fails, use sudo cat
        result = subprocess.run(['sudo', 'cat', '/etc/hosts'], capture_output=True, text=True, check=True)
        return result.stdout

def add_dns_host(ip, hostname, auto=False):
    entry = f'\n{ip}\t{hostname}\n'
    try:
        # Read current hosts file
        content = read_hosts_file()

        # Check if the hostname is already present
        if hostname in content:
            logging.info(f"[green bold]{hostname}[/] already exists in [violet bold]/etc/hosts[/].")
            return

        if not auto:
            # Ask user for confirmation
            choice = console.input(f"[[magenta]ASK[/]] Do you want to add [green bold]'{ip} {hostname}'[/] to [violet bold]/etc/hosts[/]? (y/N): ").strip().lower()
        else:
            # always Yes when auto are enabled
            choice = 'y'

        if choice == 'y':
            # Append entry using sudo, suppress tee output
            subprocess.run(
                ['sudo', 'tee', '-a', '/etc/hosts'],
                input=entry.encode(),
                stdout=subprocess.DEVNULL,  # <--- Hide standard output
                stderr=subprocess.DEVNULL,  # <--- Hide standard error
                check=True
            )
            
            logging.info(f"Hostname: [green bold]{hostname}[/] successfully added to [violet bold]/etc/hosts[/]")
        else:
            logging.info("Skipped adding to [violet bold]/etc/hosts[/].")

    except Exception as e:
        logging.exception(f"Failed to update hosts file: {e}")
