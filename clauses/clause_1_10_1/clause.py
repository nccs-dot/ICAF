from core.clause import BaseClause
from clauses.clause_1_10_1.tc1_icmp import TC1ICMPIPv4
from clauses.clause_1_10_1.tc2_icmp import TC2ICMPIPv6


class Clause_1_10_1(BaseClause):

    def __init__(self, context):
        super().__init__(context)
        self.add_testcase(TC1ICMPIPv4())
        self.add_testcase(TC2ICMPIPv6())
