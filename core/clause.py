class BaseClause:

    def __init__(self, context):

        self.context = context
        self.testcases = []

    def add_testcase(self, tc):

        self.testcases.append(tc)

    def run(self):

        results = []

        for tc in self.testcases:

            # Set active testcase in runtime context
            self.context.current_testcase = tc

            result = tc.run(self.context)

            results.append(result)

            # Clear after execution (safe practice)
            self.context.current_testcase = None

        return results