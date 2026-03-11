import uuid
from datetime import datetime
from evidence.manager import EvidenceManager


class RuntimeContext:
    """
    Shared runtime state used across the TCAF framework.
    """

    def __init__(self, clause=None, section=None, ssh_user=None, ssh_ip=None, ssh_password=None, snmp_user=None, snmp_auth_pass=None, snmp_priv_pass=None):

        self.execution_id = str(uuid.uuid4())

        self.start_time = datetime.utcnow()

        # CLI parameters
        self.clause = clause
        self.section = section
        self.ssh_user = ssh_user
        self.ssh_ip = ssh_ip
        self.ssh_password = ssh_password
        self.snmp_user = snmp_user
        self.snmp_auth_pass = snmp_auth_pass
        self.snmp_priv_pass = snmp_priv_pass

        # Core subsystems (initialized later)
        self.ssh_connection = None
        self.terminal_manager = None

        # Device information
        self.device_type = None
        self.device_info = {}

        # Adapter
        self.adapter = None

        # Evidence tracking
        self.evidence = EvidenceManager()

        self.current_testcase = None

        self.pcap_process = None
        self.pcap_file = None

        self.browser = None

        self.dut_model = "Metasploitable 2"
        self.dut_serial = "332373013881"
        self.dut_firmware = "7.0.0.0.6365"

        self.dut_name = None
        self.dut_version = None
        self.os_hash = None
        self.config_hash = None

        self.itsar_section = "1.1 Access and Authorization"
        self.itsar_requirement = "1.1.1 Management Protocols Entity Mutual Authentication"

    def summary(self):
        """
        Return basic execution summary.
        """

        return {
            "execution_id": self.execution_id,
            "clause": self.clause,
            "section": self.section,
            "device_type": self.device_type,
            "start_time": str(self.start_time),
        }