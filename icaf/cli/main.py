import typer
import time
import os
import yaml

from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live

from icaf.config.settings import initialize_directories
from icaf.utils.logger import logger
from icaf.core.engine import Engine

# Load .env
load_dotenv()

console = Console()

DEFAULT_PROFILE = "default"

app = typer.Typer(
    help="ICAF - ITSAR Compliance Automation Framework"
)

profile_app = typer.Typer(help="Manage DUT profiles")
app.add_typer(profile_app, name="profile")


def show_banner():
    banner = """
██╗ ██████╗ █████╗ ███████╗
██║██╔════╝██╔══██╗██╔════╝
██║██║     ███████║█████╗
██║██║     ██╔══██║██╔══╝
██║╚██████╗██║  ██║██║
╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝
"""
    title = Text(banner, style="bold cyan")
    subtitle = Text(
        "ITSAR Compliance Automation Framework",
        style="bold white"
    )

    console.print(
        Panel(
            Align.center(title),
            border_style="bright_magenta",
            padding=(1, 4)
        )
    )

    console.print(Align.center(subtitle))
    console.print()


@app.command()
def run(
    clause: str = typer.Option(None, "--clause"),
    section: str = typer.Option(None, "--section"),
    profile: str = typer.Option(DEFAULT_PROFILE, "--profile"),
    oam: str = typer.Option(None, "--oam"),
):

    show_banner()
    initialize_directories()

    logger.info("ICAF CLI started")
    console.print(f"[bold cyan]Using DUT profile:[/bold cyan] {profile}\n")

    # Load from ENV (no prompts)
    ssh_user = os.getenv("SSH_USER")
    ssh_ip = os.getenv("SSH_IP")
    ssh_password = os.getenv("SSH_PASSWORD")

    snmp_user = os.getenv("SNMP_USER")
    snmp_auth_pass = os.getenv("SNMP_AUTH_PASS")
    snmp_priv_pass = os.getenv("SNMP_PRIV_PASS")
    snmp_community = os.getenv("SNMP_COMMUNITY")

    web_login_url = os.getenv("WEB_LOGIN_URL")
    web_username = os.getenv("WEB_USERNAME")
    web_password = os.getenv("WEB_PASSWORD")
    testbed_diagram = os.getenv("TESTBED_DIAGRAM")

    # Fix condition bug
    if clause in ["1.1.1", "1.1"]:
        logger.info("SNMP/Web config loaded from .env")

    oam_context = None

    if oam:
        console.print("\n[bold cyan]Processing OAM Excel...[/bold cyan]\n")

        from icaf.oam.oam_manager import process_oam

        oam_context = process_oam(oam, ssh_ip)

        console.print(f"[green]Detected Protocols:[/green] {oam_context['raw_protocols']}")
        console.print(f"[green]Verified Protocols:[/green] {oam_context['verified_protocols']}\n")

    engine = Engine(
        clause=clause,
        section=section,
        profile=profile,
        ssh_user=ssh_user,
        ssh_ip=ssh_ip,
        ssh_password=ssh_password,
        snmp_user=snmp_user,
        snmp_auth_pass=snmp_auth_pass,
        snmp_priv_pass=snmp_priv_pass,
        web_login_url=web_login_url,
        web_username=web_username,
        web_password=web_password,
        snmp_community=snmp_community,
        testbed_diagram=testbed_diagram,
        oam_context=oam_context
    )

    console.print()
    console.print("[bold magenta]Initializing compliance engine[/bold magenta]")

    spinner = Spinner("dots", text="Preparing runtime environment")

    with Live(spinner, console=console, refresh_per_second=12):
        time.sleep(1)

    engine.start()


def main():
    app()


if __name__ == "__main__":
    main()