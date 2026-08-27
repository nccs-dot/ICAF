"""
Clause 1.1.3 - Role Based Access Control (RBAC)

Registers the test cases that validate the DUT's RBAC implementation:

  TC1 - RBAC feature availability (create >=3 users under different roles)
  TC2 - Role command authorization (authorized ops succeed, unauthorized denied)
  TC3 - Allowed operations per role (enforcement matches DUT-declared policy)
  TC4 - User creation without a role (auto-assigned default OR rejected)
"""

from icaf.core.clause import BaseClause
from .tc1 import TC1RBACFeatureAvailability
from .tc2 import TC2RoleCommandAuthorization
from .tc3 import TC3AllowedOperationsPerRole
from .tc4 import TC4UserCreationWithoutRole


class Clause_1_1_3(BaseClause):

    def __init__(self, context):

        super().__init__(context)

        self.add_testcase(TC1RBACFeatureAvailability())
        self.add_testcase(TC2RoleCommandAuthorization())
        self.add_testcase(TC3AllowedOperationsPerRole())
        self.add_testcase(TC4UserCreationWithoutRole())