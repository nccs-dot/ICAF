import typer
import time

from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live

from config.settings import initialize_directories
from utils.logger import logger
from core.engine import Engine

console = Console()

DEFAULT_SSH_USER = "msfadmin"
DEFAULT_SSH_IP = "10.143.115.214"
DEFAULT_SSH_PASSWORD = "msfadmin"

DEFAULT_SNMP_USER = "snmpuser"
DEFAULT_SNMP_AUTH_PASS = "authpass"
DEFAULT_SNMP_PRIV_PASS = "privpass"

DEFAULT_WEB_USERNAME = "admin"
DEFAULT_WEB_PASSWORD = "123"

app = typer.Typer(
    help="TCAF - Telecom Compliance Automation Framework"
)


def show_banner():

    banner = """
████████╗ ██████╗ █████╗ ███████╗
╚══██╔══╝██╔════╝██╔══██╗██╔════╝
   ██║   ██║     ███████║█████╗
   ██║   ██║     ██╔══██║██╔══╝
   ██║   ╚██████╗██║  ██║██║
   ╚═╝    ╚═════╝╚═╝  ╚═╝╚═╝
"""

    title = Text(banner, style="bold cyan")

    subtitle = Text(
        "Telecom Compliance Automation Framework",
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
    clause: str = typer.Option(None, "--clause", help="Run a specific clause"),
    section: str = typer.Option(None, "--section", help="Run a section of clauses"),
):

    show_banner()

    initialize_directories()

    logger.info("TCAF CLI started")

    console.print("[bold cyan]SSH Connection Setup[/bold cyan]\n")

    ssh_user = typer.prompt("Enter SSH username", default=DEFAULT_SSH_USER)

    ssh_ip = typer.prompt("Enter DuT IP", default=DEFAULT_SSH_IP)

    ssh_password = typer.prompt(
        "Enter SSH password",
        default=DEFAULT_SSH_PASSWORD,
        hide_input=True
    )

    snmp_user = None
    snmp_auth_pass = None
    snmp_priv_pass = None

    web_login_url = None
    web_username = None
    web_password = None

    if clause == "1.1.1":

        console.print("\n[bold yellow]SNMPv3 Configuration[/bold yellow]\n")

        snmp_user = typer.prompt(
            "Enter SNMPv3 username",
            default=DEFAULT_SNMP_USER
        )

        snmp_auth_pass = typer.prompt(
            "Enter SNMPv3 auth password",
            default=DEFAULT_SNMP_AUTH_PASS,
            hide_input=True
        )

        snmp_priv_pass = typer.prompt(
            "Enter SNMPv3 priv password",
            default=DEFAULT_SNMP_PRIV_PASS,
            hide_input=True
        )

        console.print("\n[bold yellow]Web Login Credentials[/bold yellow]\n")

        web_login_url = typer.prompt(
            "Enter Web Login URL",
            default=f"http://{ssh_ip}/dvwa/login.php"
        )

        web_username = typer.prompt(
            "Enter Web username",
            default=DEFAULT_WEB_USERNAME
        )

        web_password = typer.prompt(
            "Enter Web password",
            default=DEFAULT_WEB_PASSWORD,
            hide_input=True
        )

    engine = Engine(
        clause=clause,
        section=section,
        ssh_user=ssh_user,
        ssh_ip=ssh_ip,
        ssh_password=ssh_password,
        snmp_user=snmp_user,
        snmp_auth_pass=snmp_auth_pass,
        snmp_priv_pass=snmp_priv_pass,
        web_login_url=web_login_url,
        web_username=web_username,
        web_password=web_password
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