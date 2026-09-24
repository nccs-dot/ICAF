class ReportFactory:
    """
    Lazy-import factory — report modules are only imported when actually needed.
    This prevents missing-package errors at startup for clauses that aren't being run.
    """

    @staticmethod
    def create(context, results):

        clause = context.clause

        if clause == "1.1.1":
            from icaf.reporting.clause_reports.clause_1_1_1_report import Clause111Report
            return Clause111Report(context, results)
        if clause == "1.6.1":
            from icaf.reporting.clause_reports.clause_1_6_1_report import Clause161Report
            return Clause161Report(context, results)
        if clause == "1.6.5":
            from icaf.reporting.clause_reports.clause_1_6_5_report import Clause165Report
            return Clause165Report(context, results)

        raise Exception(f"No report template for clause {clause}")