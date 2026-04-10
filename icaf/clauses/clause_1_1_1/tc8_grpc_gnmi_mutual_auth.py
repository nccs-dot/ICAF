"""
TC8 — gRPC/gNMI Mutual Authentication: positive and negative cases.
Test Scenario 1.1.1.8
"""

from icaf.core.testcase import TestCase
from icaf.core.step_runner import StepRunner
from icaf.steps.command_step import CommandStep
from icaf.steps.expect_one_of_step import ExpectOneOfStep
from icaf.steps.screenshot_step import ScreenshotStep
from icaf.steps.pcap_start_step import PcapStartStep
from icaf.steps.pcap_stop_step import PcapStopStep
from icaf.steps.analyze_pcap_step import AnalyzePcapStep
from icaf.steps.wireshark_packet_screenshot_step import WiresharkPacketScreenshotStep
from icaf.steps.session_reset_step import SessionResetStep
from icaf.steps.clear_terminal_step import ClearTerminalStep
from icaf.utils.logger import logger
from .ssh_mixin import SSHMixin


class TC8GRPCGNMIMutualAuth(TestCase, SSHMixin):
    protocol = "grpc"
    """
    Test Scenario 1.1.1.8 — Configure and verify mutual authentication
    over gRPC/gNMI.

    Positive case:  valid CA cert + client cert + correct credentials
                    → DUT returns token_id

    Negative case:  valid CA cert + client cert + wrong password
                    → DUT returns error, no token_id

    Pre-configuration performed here:
      1. Generate CA key/cert, gRPC client key/cert, PKCS#12 bundle on tester.
      2. Transfer grpc.p12 and ca.pem to DUT via SFTP.
      3. Import into DUT PKI domain, enable gRPC, create local user.
    """

    PKI_DIR   = "/opt/grpcurl/grpc-pki"
    GRPC_PORT = "50051"

    def __init__(self):
        super().__init__(
            "TC8_GRPC_GNMI_MUTUAL_AUTH",
            "Configure and verify mutual authentication over gRPC/gNMI",
        )

    # ── certificate generation ─────────────────────────────────────────────

    def _generate_certificates(self, context):
        """Generate CA self-signed cert, gRPC client key/cert, and PKCS#12 bundle."""
        pki    = self.PKI_DIR
        dut_cn = context.profile.get("grpc.dut_cn", context.ssh_ip)

        cert_cmds = [
            (f"mkdir -p {pki} && cd {pki}",
             ["$", "#", pki]),
            (f"openssl req -x509 -newkey rsa:2048 -keyout ca.key -out ca.pem "
             f"-sha256 -days 3650 -nodes "
             f"-subj '/C=IN/ST=Lab/L=Cybberlab/O=CyberLab-CA'",
             ["$", "#", "writing RSA", "done"]),
            (f"openssl ecparam -name prime256v1 -genkey -noout -out {pki}/grpc.key",
             ["$", "#", "writing EC", "done"]),
            (f"openssl req -new -key {pki}/grpc.key -out {pki}/grpc.csr "
             f"-subj '/CN={dut_cn}'",
             ["$", "#", "done"]),
            (f"openssl x509 -req -in {pki}/grpc.csr "
             f"-CA {pki}/ca.pem -CAkey {pki}/ca.key "
             f"-CAcreateserial -out {pki}/grpc.pem -days 825 -sha256",
             ["$", "#", "done"]),
            (f"openssl pkcs12 -export "
             f"-inkey {pki}/grpc.key -in {pki}/grpc.pem "
             f"-name grpc-local-cert -out {pki}/grpc.p12 -passout pass:",
             ["$", "#", "done"]),
        ]

        # Use ssh_run_commands format: list of (cmd, expected) tuples
        for cmd, expected in cert_cmds:
            StepRunner([CommandStep("tester", cmd, settle_time=4)]).run(context)
            ExpectOneOfStep("tester", expected, timeout=12).execute(context)

        ScreenshotStep(
            "tester",
            caption="TC8 Step 1 — CA certificate, gRPC server key/cert, and PKCS#12 bundle generated successfully",
        ).execute(context)
        logger.info("TC8: PKI certificates and PKCS#12 bundle generated")

    # ── transfer to DUT ────────────────────────────────────────────────────

    def _transfer_to_dut(self, context):
        """Upload grpc.p12 and ca.pem to DUT root via a single SFTP session."""
        pki = self.PKI_DIR

        # SSHMixin opens one session and uploads both files efficiently
        self.sftp_upload_multiple(context, [
            (f"{pki}/grpc.p12", "/grpc.p12"),
            (f"{pki}/ca.pem",   "/ca.pem"),
        ])

        ScreenshotStep(
            "tester",
            caption="TC8 Step 2 — PKCS#12 certificate bundle and CA certificate transferred to DUT via SFTP",
        ).execute(context)
        logger.info("TC8: Certificates transferred to DUT")

    # ── DUT PKI + gRPC configuration ──────────────────────────────────────

    def _configure_dut(self, context):
        """SSH into DUT as admin and configure PKI import, gRPC, and local user."""
        grpc_user  = context.profile.get("grpc.dut_user",     "Test1")
        grpc_pass  = context.profile.get("grpc.dut_password", "Admin@123")
        pki_domain = context.profile.get("grpc.pki_domain",   "grpc_pki")
        port       = context.profile.get("grpc.port",         self.GRPC_PORT)

        self.ssh_open_session(context)

        self.ssh_run_commands(context, [
            "sys",
            # Import CA cert
            (f"pki import domain {pki_domain} pem ca filename ca.pem",
             ["finger print", "Is the finger print correct", "Y/N", "#"]),
            ("Y", ["#", ">", "$"]),
            # Import PKCS#12 client cert
            (f"pki import domain {pki_domain} p12 local filename grpc.p12",
             ["password", "Please input", "key pair name", "#"]),
            ("",         ["key pair", "#"]),   # blank password
            ("grpc-pki", ["#", ">", "$"]),     # key pair name
            # Verify
            (f"display pki certificate domain {pki_domain} ca",
             ["Certificate", "Issuer", "#"]),
            (f"display pki certificate domain {pki_domain} local",
             ["Certificate", "Subject", "#"]),
            # Enable gRPC
            (f"grpc pki domain {pki_domain}", ["#", ">", "$"]),
            ("grpc enable",                   ["#", ">", "$"]),
            (f"grpc port {port}",             ["#", ">", "$"]),
            # Create local gRPC user
            (f"local-user {grpc_user} class manage",            ["#", "new local"]),
            (f"password simple {grpc_pass}",                    ["#", ">", "$"]),
            ("authorization-attribute user-role network-admin", ["#", ">", "$"]),
            ("service-type https",                              ["#", ">", "$"]),
            ("quit",                                            ["#", ">", "$"]),
            ("save force",                                      ["saved", "#", "Y/N"]),
        ])

        ScreenshotStep(
            "tester",
            caption="TC8 Step 3 — PKI domain configured, gRPC enabled with mutual TLS, gRPC user created on DUT",
        ).execute(context)
        self.ssh_close_session(context)
        logger.info("TC8: DUT PKI and gRPC configured")

    # ── grpcurl helper ─────────────────────────────────────────────────────

    def _grpcurl_cmd(self, context, *, password: str) -> str:
        pki       = self.PKI_DIR
        grpc_user = context.profile.get("grpc.dut_user", "Test1")
        port      = context.profile.get("grpc.port",     self.GRPC_PORT)

        return (
            f"grpcurl -insecure "
            f"-cert {pki}/grpc.pem -key {pki}/grpc.key -cacert {pki}/ca.pem "
            f"-d '{{\"user_name\": \"{grpc_user}\", \"password\": \"{password}\"}}' "
            f"{context.ssh_ip}:{port} grpc_service.GrpcService.Login"
        )

    # ── positive case ──────────────────────────────────────────────────────

    def _positive_case(self, context):
        """Valid credentials → DUT returns token_id."""
        grpc_pass = context.profile.get("grpc.dut_password", "Admin@123")
        port      = context.profile.get("grpc.port",         self.GRPC_PORT)

        token_p = ["token_id", "token"]
        error_p = ["Failed to login", "ERROR", "Unauthenticated",
                   "Code: Unknown", "rpc error"]

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc8_grpc_positive.pcapng"),
            CommandStep("tester", self._grpcurl_cmd(context, password=grpc_pass), settle_time=6),
        ]).run(context)

        pattern, _ = ExpectOneOfStep(
            "tester", token_p + error_p, timeout=15
        ).execute(context)

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep(
            "tester",
            caption="TC8 Step 4 — gRPC Login RPC with valid credentials returned token_id, confirming mutual TLS authentication",
        ).execute(context)

        if any(tp in pattern for tp in token_p):
            logger.info("TC8 Positive: token_id returned — mutual auth confirmed")
            StepRunner([
                AnalyzePcapStep(f"tcp.port == {port}"),
                WiresharkPacketScreenshotStep(
                    "tls",
                    caption="TC8 Step 4 — Wireshark shows TLS 1.3 mutual authentication handshake completed for gRPC session",
                ),
                ClearTerminalStep("tester"),
            ]).run(context)
            return True

        logger.error("TC8 Positive: gRPC auth failed — '%s'", pattern)
        StepRunner([ClearTerminalStep("tester")]).run(context)
        return False

    # ── negative case ──────────────────────────────────────────────────────

    def _negative_case(self, context):
        """Wrong password → DUT returns error, no token_id."""
        bad_pass = context.profile.get("grpc.bad_password", "Admin")
        port     = context.profile.get("grpc.port",         self.GRPC_PORT)

        error_p = ["Failed to login", "ERROR", "Unauthenticated",
                   "Code: Unknown", "rpc error"]
        token_p = ["token_id", "token"]

        StepRunner([
            PcapStartStep(interface="eth0", filename="tc8_grpc_negative.pcapng"),
            CommandStep("tester", self._grpcurl_cmd(context, password=bad_pass), settle_time=6),
        ]).run(context)

        pattern, _ = ExpectOneOfStep(
            "tester", error_p + token_p, timeout=15
        ).execute(context)

        StepRunner([PcapStopStep()]).run(context)
        ScreenshotStep(
            "tester",
            caption="TC8 Step 5 — gRPC Login RPC with wrong password returned error, no token_id issued by DUT",
        ).execute(context)

        if any(tp in pattern for tp in token_p):
            logger.error("TC8 Negative: DUT issued token for wrong credentials — FAIL")
            StepRunner([ClearTerminalStep("tester")]).run(context)
            return False

        logger.info("TC8 Negative: DUT correctly rejected wrong credentials — '%s'", pattern)
        StepRunner([
            AnalyzePcapStep(f"tcp.port == {port}"),
            WiresharkPacketScreenshotStep(
                "tls",
                caption="TC8 Step 5 — Wireshark confirms gRPC unauthenticated response, TLS session closed after credential failure",
            ),
            ClearTerminalStep("tester"),
        ]).run(context)
        return True

    # ── entry point ────────────────────────────────────────────────────────

    def run(self, context):
        self._generate_certificates(context)
        self._transfer_to_dut(context)
        self._configure_dut(context)

        pos_ok = self._positive_case(context)
        neg_ok = self._negative_case(context)

        StepRunner([SessionResetStep("tester", post_reset_delay=4)]).run(context)

        if pos_ok and neg_ok:
            self.pass_test()
        else:
            logger.warning(
                "TC8 breakdown — positive=%s  negative=%s", pos_ok, neg_ok
            )
            self.fail_test()
        return self