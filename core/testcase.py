class TestCase:

    def __init__(self, name, description):

        self.name = name
        self.description = description

        self.steps = []
        self.evidence = []
        self.status = "NOT_RUN"

    def add_step(self, step):

        self.steps.append(step)

    def add_evidence(self, command=None, output=None, screenshot=None):

        self.evidence.append({
            "command": command,
            "output": output,
            "screenshot": screenshot
        })

    def pass_test(self):

        self.status = "PASS"

    def fail_test(self):

        self.status = "FAIL"

    def run(self, context):

        context.current_testcase = self.name

        try:

            for step in self.steps:

                result = step.execute(context)

                if result:
                    self.add_evidence(result)

            self.pass_test()

        except Exception as e:

            self.fail_test()

        return self