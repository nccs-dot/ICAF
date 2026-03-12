import subprocess
from core.step import Step
from utils.logger import logger


class AnalyzePcapStep(Step):

    def __init__(self, filter_expr):

        super().__init__("Analyze PCAP")

        self.filter_expr = filter_expr

    def execute(self, context):

        pcap = context.pcap_file

        cmd = [
            "tshark",
            "-r", pcap,
            "-Y", self.filter_expr,
            "-T", "fields",
            "-e", "frame.number"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        frames = result.stdout.strip().split("\n")

        if not frames or frames == [""]:
            raise Exception("No matching packet found")

        frame_number = frames[0]

        logger.info(f"Matched packet frame: {frame_number}")

        context.matched_frame = frame_number