import os
import time
import yaml
import typer

from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live

from icaf.config.settings import initialize_directories
from icaf.utils.logger import logger
from icaf.core.engine import Engine
from icaf.clauses.catalog import clause_names
from icaf.cli.preflight import register_doctor_command

console = Console()

DEFAULT_SSH_USER = "root"
DEFAULT_SSH_IP = "10.80.127.211"
DEFAULT_SSH_PASSWORD = "reaper@123"

DEFAULT_SNMP_USER = "snmpuser"
DEFAULT_SNMP_AUTH_PASS = "authpass"
DEFAULT_SNMP_PRIV_PASS = "privpass"
DEFAULT_SNMP_COMMUNITY = "community"

DEFAULT_WEB_USERNAME = "admin"
DEFAULT_WEB_PASSWORD = "123"

DEFAULT_PROFILE = "default"

app = typer.Typer(
    help="ICAF - ITSAR Compliance Automation Framework"
)

profile_app = typer.Typer(help="Manage DUT profiles")
app.add_typer(profile_app, name="profile")

# Register preflight doctor command
register_doctor_command(app)


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
    clause: str = typer.Option(None, "--clause", help="Run a specific clause"),
    section: str = typer.Option(None, "--section", help="Run a section of clauses"),
    profile: str = typer.Option(
        DEFAULT_PROFILE,
        "--profile",
        help="DUT profile configuration (linux, openwrt, cisco, etc)"
    ),
    oam: str = typer.Option(
        None,
        "--oam",
        help="Path to OAM Excel file"
    ),
):

    show_banner()

    if clause and clause not in clause_names():
        raise typer.BadParameter(f"Unsupported clause '{clause}'. Available clauses: {', '.join(clause_names())}")

    initialize_directories()

    logger.info("ICAF CLI started")

    console.print(f"[bold cyan]Using DUT profile:[/bold cyan] {profile}\n")

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
    snmp_community = None

    web_login_url = None
    web_username = None
    web_password = None

    if clause == "1.2.4":
        # Password Policy — SSH only, no SNMP or web credentials needed
        console.print(
            "\n[bold green]Clause 1.2.4 — Password Policy Compliance[/bold green]\n"
            "Only SSH credentials are required for this clause.\n"
        )

    elif clause == "1.9.3":
        # Vulnerability Scanning — Authenticated/Credentialed audit against DUT IP
        console.print(
            "\n[bold green]Clause 1.9.3 — Vulnerability Scanning[/bold green]\n"
            "Authenticated vulnerability scan: SSH target credentials will be used for auditing.\n"
        )

    elif clause == "1.2.1":
        # Authentication Policy — SSH only, no SNMP or web credentials needed
        console.print(
            "\n[bold green]Clause 1.2.1 — Authentication Policy[/bold green]\n"
            "Authentication Policy check: SFTP, SSH, SCP \n"
        )

    elif clause in ["1.1.1", "1.1"]:

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

        snmp_community = typer.prompt(
            "Enter SNMPv2 community",
            default=DEFAULT_SNMP_COMMUNITY,
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

    testbed_diagram = os.getenv("TESTBED_DIAGRAM")
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


@profile_app.command("create")
def create_profile():

    console.print("\n[bold cyan]Create New DUT Profile[/bold cyan]\n")

    profile_name = typer.prompt("Profile name")

    template_path = "icaf/profile/default.yaml"

    if not os.path.exists(template_path):
        console.print("[red]Default profile template not found![/red]")
        raise typer.Exit()

    with open(template_path) as f:
        template = yaml.safe_load(f)

    def walk_config(config, prefix=""):

        for key, value in config.items():

            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):

                console.print(f"\n[bold yellow]{full_key}[/bold yellow]")
                walk_config(value, full_key)

            elif isinstance(value, list):

                default_value = ", ".join(str(x) for x in value)

                user_input = typer.prompt(
                    f"{full_key}",
                    default=default_value
                )

                config[key] = [x.strip() for x in user_input.split(",")]

            else:

                user_input = typer.prompt(
                    f"{full_key}",
                    default=str(value)
                )

                config[key] = user_input

    walk_config(template)

    os.makedirs("icaf/profile", exist_ok=True)

    output_path = f"icaf/profile/{profile_name}.yaml"

    with open(output_path, "w") as f:
        yaml.dump(template, f, sort_keys=False)

    console.print(f"\n[bold green]Profile created:[/bold green] {output_path}\n")


@profile_app.command("list")
def list_profiles():

    console.print("\n[bold cyan]Available Profiles[/bold cyan]\n")

    profile_dir = "icaf/profile"

    if not os.path.exists(profile_dir):
        console.print("No profiles directory found.")
        return

    files = os.listdir(profile_dir)

    yaml_files = [f.replace(".yaml", "") for f in files if f.endswith(".yaml")]

    if not yaml_files:
        console.print("No profiles found.")
        return

    for p in yaml_files:
        console.print(f"• {p}")

    console.print()


def main():
    app()


if __name__ == "__main__":
    main()