import os
from datetime import datetime


class EvidenceManager:

    def __init__(self):
        self.date_prefix = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.run_dir = "output"
        os.makedirs(self.run_dir, exist_ok=True)

    def testcase_dir(self, clause, testcase):
        # Normalize: accept object or string
        if hasattr(testcase, 'name'):
            tc_name = testcase.name
        elif not isinstance(testcase, str):
            tc_name = testcase.__class__.__name__
        else:
            tc_name = str(testcase)

        path = os.path.join(self.run_dir, str(clause), tc_name)
        os.makedirs(os.path.join(path, "screenshots"), exist_ok=True)
        os.makedirs(os.path.join(path, "pcap"), exist_ok=True)
        os.makedirs(os.path.join(path, "logs"), exist_ok=True)
        return path

    def screenshot_path(self, clause, testcase):
        base = self.testcase_dir(clause, testcase)
        return f"{base}/screenshots"

    def get_timestamped_filename(self, base_name):
        return f"{self.date_prefix}_{base_name}"
