class BaseClause:

    def __init__(self, context):

        self.context = context
        self.testcases = []

    def add_testcase(self, tc):

        self.testcases.append(tc)

    def run(self):

        results = []

        oam_context = getattr(self.context, "oam_context", None)

        allowed_protocols = None

        if oam_context:
            allowed_protocols = oam_context.get("verified_protocols", [])

        for tc in self.testcases:

            # FILTER LOGIC HERE
            protocol = getattr(tc, "protocol", None)

            if allowed_protocols is not None and protocol:
                if protocol not in allowed_protocols:
                    from icaf.utils.logger import logger
                    logger.info(f"Skipping {tc.name} (protocol={protocol} not available)")
                    continue

            # Set active testcase in runtime context
            self.context.current_testcase = tc

            result = tc.run(self.context)

            results.append(result)

            # Clear after execution (safe practice)
            self.context.current_testcase = None

        return results