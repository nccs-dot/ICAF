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
    
    # Always ask for DuT IP (needed by all clauses)
    dut_ip = input("Enter DuT IP address: ")

    ssh_user = None
    ssh_password = None

    # Only ask for SSH credentials for SSH-based clauses
    NON_SSH_CLAUSES = {"1.10.1"}
    if clause not in NON_SSH_CLAUSES:
        ssh_user = input("Enter SSH username: ")
        ssh_password = input("Enter SSH password: ")

    engine = Engine(
        clause=clause,
        section=section,
        ssh_user=ssh_user,
        ssh_ip=dut_ip,
        ssh_password=ssh_password
    )

    engine.start()

def main():
    app()


if __name__ == "__main__":
    main()