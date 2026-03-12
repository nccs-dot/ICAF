from reporting.report_factory import ReportFactory
from utils.logger import logger


class ReportManager:

    def generate(self, context, results):

        logger.info("Generating compliance report")
        print(context.evidence.__dict__)

        report = ReportFactory.create(context, results)
        path = report.generate(context, results)

        logger.info(f"Report generated: {path}")

        return path