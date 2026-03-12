import os
from datetime import datetime


class EvidenceManager:

    def __init__(self):

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        self.run_dir = f"output/runs/{timestamp}"

        os.makedirs(self.run_dir, exist_ok=True)

    def testcase_dir(self, clause, testcase):

        path = f"{self.run_dir}/{clause}/{testcase}"

        os.makedirs(path, exist_ok=True)

        os.makedirs(f"{path}/screenshots", exist_ok=True)
        os.makedirs(f"{path}/logs", exist_ok=True)
        os.makedirs(f"{path}/pcap", exist_ok=True)

        return path

    def screenshot_path(self, clause, testcase):

        base = self.testcase_dir(clause, testcase)

        return f"{base}/screenshots"