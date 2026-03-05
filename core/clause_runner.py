from utils.logger import logger
from clauses.registry import CLAUSE_REGISTRY


class ClauseRunner:

    def __init__(self, context):
        self.context = context

    def run(self):

        clause_id = self.context.clause

        if clause_id not in CLAUSE_REGISTRY:
            raise ValueError(f"Clause {clause_id} not registered")

        clause_class = CLAUSE_REGISTRY[clause_id]

        logger.info(f"Loading clause {clause_id}")

        clause = clause_class(self.context)

        logger.info(f"Executing clause {clause_id}")

        results = clause.run()

        return results