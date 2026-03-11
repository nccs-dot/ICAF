import subprocess
from core.step import Step
from utils.logger import logger


class PcapStartStep(Step):

    def __init__(self, interface="eth0", filename="capture.pcapng"):

        super().__init__("Start packet capture")

        self.interface = interface
        self.filename = filename
        self.process = None

    def execute(self, context):

        clause = context.clause
        testcase = context.current_testcase

        path = context.evidence.testcase_dir(clause, testcase)

        timestamped_name = context.evidence.get_timestamped_filename(self.filename)
        pcap_file = f"{path}/pcap/{timestamped_name}"

        logger.info(f"Starting PCAP capture: {pcap_file}")

        self.process = subprocess.Popen([
            "tcpdump",
            "-i", self.interface,
            "-w", pcap_file
        ])

        context.pcap_process = self.process
        context.pcap_file = pcap_file