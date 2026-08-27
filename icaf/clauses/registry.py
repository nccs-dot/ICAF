def _load_clause_111():
    from icaf.clauses.clause_1_1_1.clause import Clause_1_1_1
    from icaf.clauses.clause_1_1_3.clause import Clause_1_1_3
    from icaf.clauses.clause_1_6_1.clause import Clause_1_6_1
    from icaf.clauses.clause_1_2_4.clause import Clause_1_2_4
    from icaf.clauses.clause_1_6_5.clause import Clause_1_6_5

    return {
        "1.1.1": Clause_1_1_1,
        "1.1.3": Clause_1_1_3,
        "1.6.1": Clause_1_6_1,
        "1.2.4": Clause_1_2_4,
    }
    return Clause_1_1_1


def _load_clause_124():
    from icaf.clauses.clause_1_2_4.clause import Clause_1_2_4
    return Clause_1_2_4


def _load_clause_161():
    from icaf.clauses.clause_1_6_1.clause import Clause_1_6_1
    return Clause_1_6_1


def _load_clause_165():
    from icaf.clauses.clause_1_6_5.clause import Clause_1_6_5
    return Clause_1_6_5

def _load_clause_113():
    from icaf.clauses.clause_1_1_3.clause import Clause_1_1_3
    return Clause_1_1_3


def _load_clause_121():
    from icaf.clauses.clause_1_2_1.clause import Clause_1_2_1
    return Clause_1_2_1

_CLAUSE_LOADERS = {
    "1.1.1": _load_clause_111,
    "1.2.4": _load_clause_124,
    "1.6.1": _load_clause_161,
    "1.6.5": _load_clause_165,
    "1.1.3": _load_clause_113,
    "1.2.1": _load_clause_121,
}


# Keep CLAUSE_REGISTRY as a dict-like proxy for backward compatibility
class _LazyRegistry(dict):
    """Load each clause independently to avoid unrelated dependencies."""

    def _load(self, key):
        if not dict.__contains__(self, key) and key in _CLAUSE_LOADERS:
            self[key] = _CLAUSE_LOADERS[key]()

    def __getitem__(self, key):
        self._load(key)
        return super().__getitem__(key)

    def __contains__(self, key):
        self._load(key)
        return dict.__contains__(self, key)


CLAUSE_REGISTRY = _LazyRegistry()
