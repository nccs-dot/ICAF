import typer
from config.settings import initialize_directories
from utils.logger import logger
from core.engine import Engine


app = typer.Typer(
    help="TCAF - Telecom Compliance Automation Framework"
)

@app.command()
def run(
    clause: str = typer.Option(None, "--clause", help="Run a specific clause"),
    section: str = typer.Option(None, "--section", help="Run a section of clauses"),
):
    initialize_directories()
    
    logger.info("TCAF CLI started")
    
    ssh_user = input("Enter SSH username: ")
    ssh_ip = input("Enter DuT IP: ")
    ssh_password = input("Enter SSH password: ")
    if clause == "1.1.1":
        snmp_user = typer.prompt("Enter SNMPv3 username")
        snmp_auth_pass = typer.prompt("Enter SNMPv3 auth password", hide_input=True)
        snmp_priv_pass = typer.prompt("Enter SNMPv3 priv password", hide_input=True)
    
    engine = Engine(
        clause=clause,
        section=section,
        ssh_user=ssh_user,
        ssh_ip=ssh_ip,
        ssh_password=ssh_password,
        snmp_user=snmp_user,
        snmp_auth_pass=snmp_auth_pass,
        snmp_priv_pass=snmp_priv_pass
    )

    engine.start()

def main():
    app()


if __name__ == "__main__":
    main()