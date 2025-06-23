from rich.console import Console

console = Console()

def logo():
    banner = r"""
    _   _          _     _   _                      _    
    | \ | |   ___  | |_  | | | |   __ _  __      __ | | __
    |  \| |  / _ \ | __| | |_| |  / _` | \ \ /\ / / | |/ /
    | |\  | |  __/ | |_  |  _  | | (_| |  \ V  V /  |   < 
    |_| \_|  \___|  \__| |_| |_|  \__,_|   \_/\_/   |_|\_\ [bold cyan]v1.0.0[/]
    
                        [blue bold]risingsunsecurities.com[/]                                 
    """

    console.print(f"[white bold]{banner}[/]")
    
def group(description: str):
    """Print formatted group banner"""
    banner = f"""
                  ╔{'═' * (len(description) + 4)}╗
╔═════════════════╣  [bold green]{description}[/]  ╠═════════════════
                  ╚{'═' * (len(description) + 4)}╝
    """
    console.print(f"[cyan]{banner}[/cyan]") 

def task(description: str):
    """Print formatted task banner"""
    banner = f"""
╔═════════════════╣  {description}
    """
    console.print(f"[bold green]{banner}[/]") 