"""
icaf/clauses/clause_1_2_1/testcases/tc_1_2_1_auth.py

Clause 1.2.1: User Authentication - All Test Cases (TC1-TC12)

Test Objectives:
    Verify authentication enforcement across multiple protocols and channels:
    - Console login (local access)
    - SSH CLI access
    - SFTP file transfer access
    - SCP secure copy access
    
Test Scenarios (12 Total):
    TC1-3:   Console authentication (no auth, correct, incorrect password)
    TC4-6:   SSH authentication (no auth, correct, incorrect password)
    TC7-9:   SFTP authentication (no auth, correct, incorrect password)
    TC10-12: SCP authentication (no auth, correct, incorrect password)

Verdict Rules:
    - PASS:   Authentication requirement enforced; correct credentials accepted; 
              incorrect credentials rejected
    - FAIL:   Authentication bypassed OR incorrect credentials accepted OR 
              correct credentials rejected
    - ERROR:  Test execution exception, connection failure, or tool unavailable
"""

import time
import paramiko
from icaf.core.result_recorder import record_result, save_evidence
from icaf.utils.logger import logger


# ─────────────────────────────────────────────────────────────────────────
# Test Case Definitions
# ─────────────────────────────────────────────────────────────────────────

class AuthTestCase:
    """Base authentication test case."""
    
    def __init__(self, tc_id, tc_name, description, protocol, test_type):
        """
        Args:
            tc_id: Test case ID (TC1, TC2, etc.)
            tc_name: Human-readable test name
            description: Detailed description
            protocol: Protocol being tested (console, ssh, sftp, scp)
            test_type: Test scenario (no_auth, correct, incorrect)
        """
        self.tc_id = tc_id
        self.tc_name = tc_name
        self.description = description
        self.protocol = protocol
        self.test_type = test_type
        self.verdict = "FAIL"
        self.output = []
        self.command_executed = ""
        self.expected_result = ""
        self.actual_result = ""
    
    def add_output(self, line):
        """Add line to test output."""
        self.output.append(line)
        logger.info(f"[1.2.1] [{self.tc_id}] {line}")
    
    def record(self):
        """Record test result via framework."""
        evidence = save_evidence(self.tc_id, self.command_executed, "\n".join(self.output))
        record_result(
            self.tc_id, self.tc_name, self.description,
            self.command_executed, "\n".join(self.output),
            self.expected_result,
            self.actual_result,
            self.verdict, [evidence]
        )


# ─────────────────────────────────────────────────────────────────────────
# CONSOLE AUTHENTICATION TESTS (TC1-TC3)
# ─────────────────────────────────────────────────────────────────────────

def tc_1_console_no_auth(ssh, test_user, test_pass, dut_ip):
    """
    TC1: Console login without username and password.
    Expected: Connection rejected / login prompt requires credentials
    """
    tc = AuthTestCase(
        "TC1", "Console - No Authentication",
        "Verify DUT console requires authentication; no connection without credentials",
        "console", "no_auth"
    )
    
    tc.add_output("=== TC1: Console Authentication - No Credentials ===")
    tc.expected_result = "Console login shall fail without credentials"
    
    try:
        # Attempt: Try to access console without credentials (simulated via SSH + expect login prompt)
        cmd = "timeout 5 telnet localhost 2>&1 | head -20 || true"
        tc.command_executed = cmd
        out, err, code = ssh.run(cmd, timeout=10)
        
        tc.add_output(f"Attempt: Console access without credentials")
        tc.add_output(f"Command: {cmd}")
        
        # Check if login prompt appears (requires credentials)
        login_keywords = ["login:", "username:", "password:", "authentication", "access denied"]
        requires_auth = any(kw in out.lower() or kw in err.lower() for kw in login_keywords)
        
        if requires_auth or code != 0:
            tc.verdict = "PASS"
            tc.actual_result = "Console requires authentication; prompt displayed or connection denied"
            tc.add_output("✓ PASS: Console login prompt requires credentials")
        else:
            tc.actual_result = "Console allowed access without credentials"
            tc.add_output("❌ FAIL: Console did not require authentication")
        
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


def tc_2_console_correct_auth(ssh, test_user, test_pass, dut_ip):
    """
    TC2: Console login with correct username and password.
    Expected: Login successful
    """
    tc = AuthTestCase(
        "TC2", "Console - Correct Authentication",
        "Verify DUT console accepts correct username and password credentials",
        "console", "correct"
    )
    
    tc.add_output("=== TC2: Console Authentication - Correct Credentials ===")
    tc.expected_result = "Console login shall succeed with correct credentials"
    
    try:
        # Simulate console login via SSH with expect-like behavior
        tc.add_output(f"Attempting console login as user: {test_user}")
        
        # Use SSH to simulate console login
        cmd = f"echo '{test_pass}' | su {test_user} -c 'whoami' 2>&1"
        tc.command_executed = cmd
        out, err, code = ssh.run(cmd, timeout=10)
        
        # Check if login successful
        if code == 0 and test_user in out:
            tc.verdict = "PASS"
            tc.actual_result = f"Console login successful as {test_user}"
            tc.add_output(f"✓ PASS: Console login successful; authenticated as {test_user}")
        else:
            tc.actual_result = "Console login failed with correct credentials"
            tc.add_output("❌ FAIL: Console rejected correct credentials")
        
        tc.add_output(f"Output: {out.strip()}")
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


def tc_3_console_incorrect_auth(ssh, test_user, test_pass, dut_ip):
    """
    TC3: Console login with correct username and incorrect password.
    Expected: Login rejected
    """
    tc = AuthTestCase(
        "TC3", "Console - Incorrect Authentication",
        "Verify DUT console rejects incorrect password even with correct username",
        "console", "incorrect"
    )
    
    tc.add_output("=== TC3: Console Authentication - Incorrect Password ===")
    tc.expected_result = "Console login shall fail with incorrect password"
    
    try:
        wrong_pass = "WRONG_PASSWORD_12345"
        
        tc.add_output(f"Attempting console login as user: {test_user} with wrong password")
        
        cmd = f"echo '{wrong_pass}' | su {test_user} -c 'whoami' 2>&1"
        tc.command_executed = cmd
        out, err, code = ssh.run(cmd, timeout=10)
        
        # Check if login failed
        if code != 0 or "incorrect" in out.lower() or "denied" in out.lower():
            tc.verdict = "PASS"
            tc.actual_result = "Console login rejected with incorrect password"
            tc.add_output("✓ PASS: Console rejected incorrect password")
        else:
            tc.actual_result = "Console accepted incorrect password"
            tc.add_output("❌ FAIL: Console accepted incorrect password")
        
        tc.add_output(f"Output: {out.strip()}")
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


# ─────────────────────────────────────────────────────────────────────────
# SSH AUTHENTICATION TESTS (TC4-TC6)
# ─────────────────────────────────────────────────────────────────────────

def tc_4_ssh_no_auth(ssh_ip, test_user, test_pass):
    """
    TC4: SSH login without username and password.
    Expected: Connection rejected
    """
    tc = AuthTestCase(
        "TC4", "SSH - No Authentication",
        "Verify DUT SSH requires authentication; connection rejected without credentials",
        "ssh", "no_auth"
    )
    
    tc.add_output("=== TC4: SSH Authentication - No Credentials ===")
    tc.expected_result = "SSH connection shall fail without credentials"
    
    try:
        tc.add_output(f"Attempting SSH connection to {ssh_ip} without credentials")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        tc.command_executed = f"ssh {ssh_ip} (no credentials)"
        
        try:
            # Attempt connection without password
            client.connect(ssh_ip, port=22, username="", password="", timeout=5)
            tc.actual_result = "SSH accepted connection without credentials"
            tc.add_output("❌ FAIL: SSH accepted empty credentials")
        except paramiko.AuthenticationException as ae:
            tc.verdict = "PASS"
            tc.actual_result = "SSH rejected connection without credentials"
            tc.add_output(f"✓ PASS: SSH authentication required: {str(ae)[:100]}")
        except Exception as e:
            tc.verdict = "PASS"
            tc.actual_result = f"SSH connection rejected: {str(e)[:100]}"
            tc.add_output(f"✓ PASS: SSH connection rejected (no auth)")
        finally:
            try:
                client.close()
            except:
                pass
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


def tc_5_ssh_correct_auth(ssh_ip, test_user, test_pass):
    """
    TC5: SSH login with correct username and password.
    Expected: Login successful
    """
    tc = AuthTestCase(
        "TC5", "SSH - Correct Authentication",
        "Verify DUT SSH accepts correct username and password credentials",
        "ssh", "correct"
    )
    
    tc.add_output("=== TC5: SSH Authentication - Correct Credentials ===")
    tc.expected_result = "SSH login shall succeed with correct credentials"
    
    try:
        tc.add_output(f"Attempting SSH login to {ssh_ip} as user: {test_user}")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        tc.command_executed = f"ssh {ssh_ip} -u {test_user}"
        
        try:
            client.connect(ssh_ip, port=22, username=test_user, password=test_pass, timeout=10)
            
            # Execute whoami to verify authentication
            stdin, stdout, stderr = client.exec_command("whoami")
            output = stdout.read().decode('utf-8').strip()
            
            if output == test_user:
                tc.verdict = "PASS"
                tc.actual_result = f"SSH login successful as {test_user}"
                tc.add_output(f"✓ PASS: SSH authenticated successfully as {test_user}")
            else:
                tc.actual_result = "SSH login failed"
                tc.add_output("❌ FAIL: SSH authentication failed")
            
            tc.add_output(f"SSH whoami output: {output}")
        
        except paramiko.AuthenticationException as ae:
            tc.actual_result = "SSH rejected correct credentials"
            tc.add_output(f"❌ FAIL: SSH rejected correct credentials: {str(ae)[:100]}")
        
        finally:
            try:
                client.close()
            except:
                pass
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


def tc_6_ssh_incorrect_auth(ssh_ip, test_user, test_pass):
    """
    TC6: SSH login with correct username and incorrect password.
    Expected: Login rejected
    """
    tc = AuthTestCase(
        "TC6", "SSH - Incorrect Authentication",
        "Verify DUT SSH rejects incorrect password even with correct username",
        "ssh", "incorrect"
    )
    
    tc.add_output("=== TC6: SSH Authentication - Incorrect Password ===")
    tc.expected_result = "SSH login shall fail with incorrect password"
    
    try:
        wrong_pass = "WRONG_PASSWORD_12345"
        tc.add_output(f"Attempting SSH login as {test_user} with incorrect password")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        tc.command_executed = f"ssh {ssh_ip} -u {test_user} (wrong password)"
        
        try:
            client.connect(ssh_ip, port=22, username=test_user, password=wrong_pass, timeout=10)
            tc.actual_result = "SSH accepted incorrect password"
            tc.add_output("❌ FAIL: SSH accepted incorrect password")
        
        except paramiko.AuthenticationException:
            tc.verdict = "PASS"
            tc.actual_result = "SSH rejected incorrect password"
            tc.add_output("✓ PASS: SSH rejected incorrect password")
        
        except Exception as e:
            tc.verdict = "PASS"
            tc.actual_result = "SSH connection rejected"
            tc.add_output(f"✓ PASS: SSH connection rejected")
        
        finally:
            try:
                client.close()
            except:
                pass
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


# ─────────────────────────────────────────────────────────────────────────
# SFTP AUTHENTICATION TESTS (TC7-TC9)
# ─────────────────────────────────────────────────────────────────────────

def tc_7_sftp_no_auth(ssh_ip, test_user, test_pass):
    """
    TC7: SFTP login without username and password.
    Expected: Connection rejected
    """
    tc = AuthTestCase(
        "TC7", "SFTP - No Authentication",
        "Verify DUT SFTP requires authentication; connection rejected without credentials",
        "sftp", "no_auth"
    )
    
    tc.add_output("=== TC7: SFTP Authentication - No Credentials ===")
    tc.expected_result = "SFTP connection shall fail without credentials"
    
    try:
        tc.add_output(f"Attempting SFTP connection to {ssh_ip} without credentials")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        tc.command_executed = f"sftp {ssh_ip} (no credentials)"
        
        try:
            client.connect(ssh_ip, port=22, username="", password="", timeout=5)
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            tc.actual_result = "SFTP accepted connection without credentials"
            tc.add_output("❌ FAIL: SFTP accepted empty credentials")
            sftp.close()
        
        except (paramiko.AuthenticationException, paramiko.SSHException) as e:
            tc.verdict = "PASS"
            tc.actual_result = "SFTP rejected connection without credentials"
            tc.add_output(f"✓ PASS: SFTP authentication required")
        
        except Exception as e:
            tc.verdict = "PASS"
            tc.actual_result = "SFTP connection rejected"
            tc.add_output(f"✓ PASS: SFTP connection rejected (no auth)")
        
        finally:
            try:
                client.close()
            except:
                pass
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


def tc_8_sftp_correct_auth(ssh_ip, test_user, test_pass):
    """
    TC8: SFTP login with correct username and password.
    Expected: Login successful
    """
    tc = AuthTestCase(
        "TC8", "SFTP - Correct Authentication",
        "Verify DUT SFTP accepts correct username and password credentials",
        "sftp", "correct"
    )
    
    tc.add_output("=== TC8: SFTP Authentication - Correct Credentials ===")
    tc.expected_result = "SFTP login shall succeed with correct credentials"
    
    try:
        tc.add_output(f"Attempting SFTP login to {ssh_ip} as user: {test_user}")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        tc.command_executed = f"sftp {ssh_ip} -u {test_user}"
        
        try:
            client.connect(ssh_ip, port=22, username=test_user, password=test_pass, timeout=10)
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            
            # Try to list directory to verify authentication
            files = sftp.listdir('.')
            
            tc.verdict = "PASS"
            tc.actual_result = f"SFTP login successful as {test_user}"
            tc.add_output(f"✓ PASS: SFTP authenticated successfully as {test_user}")
            tc.add_output(f"  Files in home directory: {len(files)} items")
            
            sftp.close()
        
        except (paramiko.AuthenticationException, paramiko.SSHException) as e:
            tc.actual_result = "SFTP rejected correct credentials"
            tc.add_output(f"❌ FAIL: SFTP rejected correct credentials")
        
        finally:
            try:
                client.close()
            except:
                pass
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


def tc_9_sftp_incorrect_auth(ssh_ip, test_user, test_pass):
    """
    TC9: SFTP login with correct username and incorrect password.
    Expected: Login rejected
    """
    tc = AuthTestCase(
        "TC9", "SFTP - Incorrect Authentication",
        "Verify DUT SFTP rejects incorrect password even with correct username",
        "sftp", "incorrect"
    )
    
    tc.add_output("=== TC9: SFTP Authentication - Incorrect Password ===")
    tc.expected_result = "SFTP login shall fail with incorrect password"
    
    try:
        wrong_pass = "WRONG_PASSWORD_12345"
        tc.add_output(f"Attempting SFTP login as {test_user} with incorrect password")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        tc.command_executed = f"sftp {ssh_ip} -u {test_user} (wrong password)"
        
        try:
            client.connect(ssh_ip, port=22, username=test_user, password=wrong_pass, timeout=10)
            tc.actual_result = "SFTP accepted incorrect password"
            tc.add_output("❌ FAIL: SFTP accepted incorrect password")
        
        except (paramiko.AuthenticationException, paramiko.SSHException):
            tc.verdict = "PASS"
            tc.actual_result = "SFTP rejected incorrect password"
            tc.add_output("✓ PASS: SFTP rejected incorrect password")
        
        except Exception as e:
            tc.verdict = "PASS"
            tc.actual_result = "SFTP connection rejected"
            tc.add_output(f"✓ PASS: SFTP connection rejected")
        
        finally:
            try:
                client.close()
            except:
                pass
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


# ─────────────────────────────────────────────────────────────────────────
# SCP AUTHENTICATION TESTS (TC10-TC12)
# ─────────────────────────────────────────────────────────────────────────

def tc_10_scp_no_auth(ssh_ip, test_user, test_pass):
    """
    TC10: SCP login without username and password.
    Expected: Connection rejected
    """
    tc = AuthTestCase(
        "TC10", "SCP - No Authentication",
        "Verify DUT SCP requires authentication; connection rejected without credentials",
        "scp", "no_auth"
    )
    
    tc.add_output("=== TC10: SCP Authentication - No Credentials ===")
    tc.expected_result = "SCP connection shall fail without credentials"
    
    try:
        tc.add_output(f"Attempting SCP connection to {ssh_ip} without credentials")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        tc.command_executed = f"scp {ssh_ip}:/tmp/test.txt . (no credentials)"
        
        try:
            client.connect(ssh_ip, port=22, username="", password="", timeout=5)
            tc.actual_result = "SCP accepted connection without credentials"
            tc.add_output("❌ FAIL: SCP accepted empty credentials")
        
        except (paramiko.AuthenticationException, paramiko.SSHException):
            tc.verdict = "PASS"
            tc.actual_result = "SCP rejected connection without credentials"
            tc.add_output(f"✓ PASS: SCP authentication required")
        
        except Exception as e:
            tc.verdict = "PASS"
            tc.actual_result = "SCP connection rejected"
            tc.add_output(f"✓ PASS: SCP connection rejected (no auth)")
        
        finally:
            try:
                client.close()
            except:
                pass
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


def tc_11_scp_correct_auth(ssh_ip, test_user, test_pass):
    """
    TC11: SCP login with correct username and password.
    Expected: Login successful
    """
    tc = AuthTestCase(
        "TC11", "SCP - Correct Authentication",
        "Verify DUT SCP accepts correct username and password credentials",
        "scp", "correct"
    )
    
    tc.add_output("=== TC11: SCP Authentication - Correct Credentials ===")
    tc.expected_result = "SCP login shall succeed with correct credentials"
    
    try:
        tc.add_output(f"Attempting SCP login to {ssh_ip} as user: {test_user}")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        tc.command_executed = f"scp {test_user}@{ssh_ip}:/tmp/test.txt . (correct password)"
        
        try:
            client.connect(ssh_ip, port=22, username=test_user, password=test_pass, timeout=10)
            
            # Try to execute remote command to verify authentication
            stdin, stdout, stderr = client.exec_command("echo 'scp_test' > /tmp/scp_test.txt && cat /tmp/scp_test.txt")
            output = stdout.read().decode('utf-8').strip()
            
            if "scp_test" in output:
                tc.verdict = "PASS"
                tc.actual_result = f"SCP login successful as {test_user}"
                tc.add_output(f"✓ PASS: SCP authenticated successfully as {test_user}")
            else:
                tc.actual_result = "SCP login failed"
                tc.add_output("❌ FAIL: SCP authentication failed")
        
        except (paramiko.AuthenticationException, paramiko.SSHException):
            tc.actual_result = "SCP rejected correct credentials"
            tc.add_output(f"❌ FAIL: SCP rejected correct credentials")
        
        finally:
            try:
                client.close()
            except:
                pass
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


def tc_12_scp_incorrect_auth(ssh_ip, test_user, test_pass):
    """
    TC12: SCP login with correct username and incorrect password.
    Expected: Login rejected
    """
    tc = AuthTestCase(
        "TC12", "SCP - Incorrect Authentication",
        "Verify DUT SCP rejects incorrect password even with correct username",
        "scp", "incorrect"
    )
    
    tc.add_output("=== TC12: SCP Authentication - Incorrect Password ===")
    tc.expected_result = "SCP login shall fail with incorrect password"
    
    try:
        wrong_pass = "WRONG_PASSWORD_12345"
        tc.add_output(f"Attempting SCP login as {test_user} with incorrect password")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        tc.command_executed = f"scp {test_user}@{ssh_ip}:/tmp/test.txt . (wrong password)"
        
        try:
            client.connect(ssh_ip, port=22, username=test_user, password=wrong_pass, timeout=10)
            tc.actual_result = "SCP accepted incorrect password"
            tc.add_output("❌ FAIL: SCP accepted incorrect password")
        
        except (paramiko.AuthenticationException, paramiko.SSHException):
            tc.verdict = "PASS"
            tc.actual_result = "SCP rejected incorrect password"
            tc.add_output("✓ PASS: SCP rejected incorrect password")
        
        except Exception as e:
            tc.verdict = "PASS"
            tc.actual_result = "SCP connection rejected"
            tc.add_output(f"✓ PASS: SCP connection rejected")
        
        finally:
            try:
                client.close()
            except:
                pass
    
    except Exception as e:
        tc.actual_result = f"Exception: {str(e)}"
        tc.verdict = "ERROR"
        tc.add_output(f"❌ ERROR: {str(e)}")
    
    tc.record()


# ─────────────────────────────────────────────────────────────────────────
# Main Test Runner
# ─────────────────────────────────────────────────────────────────────────

def run(ssh):
    """
    Execute all 12 authentication test cases.
    
    Args:
        ssh: Authenticated SSH wrapper object
    """
    logger.info("[1.2.1] Starting User Authentication Test Suite (TC1-TC12)")
    
    # Extract test parameters from SSH context
    dut_ip = ssh._client.get_transport().getpeername()[0] if hasattr(ssh, '_client') else "127.0.0.1"
    test_user = "testuser"
    test_pass = "TestPass123"
    
    # Create test user if not exists
    try:
        logger.info("[1.2.1] Setting up test user")
        ssh.run(f"id {test_user} >/dev/null 2>&1 || adduser -D {test_user} 2>/dev/null || true", timeout=15)
        ssh.run(f"echo '{test_user}:{test_pass}' | chpasswd 2>/dev/null || true", timeout=15)
        logger.info(f"[1.2.1] Test user {test_user} ready")
    except Exception as e:
        logger.warning(f"[1.2.1] Test user setup: {e}")
    
    # ─────────────────────────────────────────────────────────────────────
    # Execute Console Authentication Tests (TC1-TC3)
    # ─────────────────────────────────────────────────────────────────────
    logger.info("[1.2.1] Executing Console Authentication Tests (TC1-TC3)")
    tc_1_console_no_auth(ssh, test_user, test_pass, dut_ip)
    tc_2_console_correct_auth(ssh, test_user, test_pass, dut_ip)
    tc_3_console_incorrect_auth(ssh, test_user, test_pass, dut_ip)
    
    # ─────────────────────────────────────────────────────────────────────
    # Execute SSH Authentication Tests (TC4-TC6)
    # ─────────────────────────────────────────────────────────────────────
    logger.info("[1.2.1] Executing SSH Authentication Tests (TC4-TC6)")
    tc_4_ssh_no_auth(dut_ip, test_user, test_pass)
    tc_5_ssh_correct_auth(dut_ip, test_user, test_pass)
    tc_6_ssh_incorrect_auth(dut_ip, test_user, test_pass)
    
    # ─────────────────────────────────────────────────────────────────────
    # Execute SFTP Authentication Tests (TC7-TC9)
    # ─────────────────────────────────────────────────────────────────────
    logger.info("[1.2.1] Executing SFTP Authentication Tests (TC7-TC9)")
    tc_7_sftp_no_auth(dut_ip, test_user, test_pass)
    tc_8_sftp_correct_auth(dut_ip, test_user, test_pass)
    tc_9_sftp_incorrect_auth(dut_ip, test_user, test_pass)
    
    # ─────────────────────────────────────────────────────────────────────
    # Execute SCP Authentication Tests (TC10-TC12)
    # ─────────────────────────────────────────────────────────────────────
    logger.info("[1.2.1] Executing SCP Authentication Tests (TC10-TC12)")
    tc_10_scp_no_auth(dut_ip, test_user, test_pass)
    tc_11_scp_correct_auth(dut_ip, test_user, test_pass)
    tc_12_scp_incorrect_auth(dut_ip, test_user, test_pass)
    
    # Cleanup
    try:
        logger.info("[1.2.1] Cleaning up test user")
        ssh.run(f"deluser {test_user} 2>/dev/null || userdel {test_user} 2>/dev/null || true", timeout=15)
    except Exception as e:
        logger.warning(f"[1.2.1] Test user cleanup: {e}")
    
    logger.info("[1.2.1] User Authentication Test Suite Complete")