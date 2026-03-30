from icaf.core.clause import BaseClause
from .tc1_snmp_v3_positive import TC1SNMPv3Positive
from .tc2_snmp_v3_invalid_credentials import TC2SNMPv3InvalidCredentials
from .tc3_ssh_mutual_auth import TC3SSHMutualAuth
from .tc4_ssh_correct_public_key import TC4SSHCorrectPublicKey
from .tc5_ssh_incorrect_public_key import TC5SSHIncorrectPublicKey
from .tc6_https_valid_login import TC6HTTPSValidLogin
from .tc7_https_invalid_login import TC7HTTPSInvalidLogin
from .tc8_grpc_gnmi_mutual_auth import TC8GRPCGNMIMutualAuth

class Clause_1_1_1(BaseClause):

    def __init__(self, context):

        super().__init__(context)

        self.add_testcase(TC1SNMPv3Positive())
        # self.add_testcase(TC2SNMPv3InvalidCredentials())
        # self.add_testcase(TC3SSHMutualAuth())
        # self.add_testcase(TC4SSHCorrectPublicKey())
        # self.add_testcase(TC5SSHIncorrectPublicKey())
        # self.add_testcase(TC6HTTPSValidLogin())
        # self.add_testcase(TC7HTTPSInvalidLogin())
        # self.add_testcase(TC8GRPCGNMIMutualAuth())

        