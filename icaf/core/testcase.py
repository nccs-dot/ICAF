class TestCase:

    def __init__(self, name, description):

        self.name = name
        self.description = description

        self.steps = []
        self.evidence = []
        self.status = "NOT_RUN"

        # Set by skip() when a TC is excluded at runtime (e.g. protocol absent).
        # None means the TC was never attempted for an unspecified reason.
        self.skip_reason: str | None = None

    def add_step(self, step):

        self.steps.append(step)

    def add_evidence(self, command=None, output=None, screenshot=None, caption=None):

        self.evidence.append({
            "command": command,
            "output": output,
            "screenshot": screenshot,
            "caption": caption,
        })

    def pass_test(self):

        self.status = "PASS"

    def fail_test(self):

        self.status = "FAIL"

    def skip(self, reason: str) -> "TestCase":
        """
        Mark this TC as not applicable with an explicit reason.

        Used when a TC is intentionally bypassed at runtime (e.g. the required
        protocol was not detected on the DUT).  The status is set to
        ``NOT_APPLICABLE`` so the report can render protocol-specific text
        rather than the generic "test not executed" message that appears for
        TCs that are simply commented out of the clause.
        """
        self.status = "NOT_APPLICABLE"
        self.skip_reason = reason
        return self

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