import subprocess
import time
import pyautogui
import shutil
from datetime import datetime
import os

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# ---------------- TERMINAL CONTROL ----------------

def launch_terminal():
    subprocess.Popen(["gnome-terminal"])
    time.sleep(3)


def focus_terminal():
    subprocess.run(["wmctrl", "-xa", "gnome-terminal"])
    time.sleep(1)


def maximize_terminal():
    pyautogui.hotkey("alt", "f10")
    time.sleep(1)


def run_visible_command(command):
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.typewrite(command + "\n", interval=0.03)


def exit_terminal():
    pyautogui.typewrite("exit\n", interval=0.05)
    time.sleep(1)


# ---------------- BACKEND EXECUTION ----------------

def _run_nmap_tcp(dut_ip: str) -> str | None:
    if not shutil.which("nmap"):
        return None
    result = subprocess.run(
        ["nmap", "-p22,80,443", "-Pn", "-n", "--open", dut_ip],
        capture_output=True,
        text=True,
    )
    return result.stdout


def _run_nmap_udp(dut_ip: str) -> str | None:
    if not shutil.which("nmap"):
        return None
    result = subprocess.run(
        ["sudo", "nmap", "-sU", "-p161", "-Pn", "-n", dut_ip],
        capture_output=True,
        text=True,
    )
    return result.stdout


# ---------------- SERVICE DETECTION ----------------

def _detect_services(tcp_output: str, udp_output: str) -> dict:
    services = {"SSH": False, "HTTP": False, "HTTPS": False, "SNMP": False}

    if tcp_output:
        out = tcp_output.lower()
        if "22/tcp" in out and "open" in out:
            services["SSH"] = True
        if "80/tcp" in out and "open" in out:
            services["HTTP"] = True
        if "443/tcp" in out and "open" in out:
            services["HTTPS"] = True

    if udp_output:
        out = udp_output.lower()
        if "161/udp" in out and "open" in out:
            services["SNMP"] = True

    return services


# ---------------- MAIN FUNCTION ----------------

def run_nmap_scan(context) -> dict:

    dut_ip = context.ssh_ip

    scan_data = {
        "test_case_id": "TC_DUT_CONFIGURATION_NMAP_SCAN",

        # TCP scan fields
        "user_input_tcp_ports": f"nmap -p22,80,443 -Pn -n --open {dut_ip}",
        "terminal_output_tcp_ports": "",
        "tcp_screenshot": "",

        # UDP scan fields
        "user_input_udp_ports": f"sudo nmap -sU -p161 -Pn -n {dut_ip}",
        "terminal_output_udp_ports": "",
        "udp_screenshot": "",

        # Legacy single-key fallback used by report intro
        "user_input": f"nmap -p22,80,443 -Pn -n --open {dut_ip}",
        "terminal_output": "",
        "screenshot": "",

        # Service flags — read by clause_1_6_1
        "SSH":   False,
        "HTTP":  False,
        "HTTPS": False,
        "SNMP":  False,
    }

    try:
        launch_terminal()
        focus_terminal()
        maximize_terminal()

        # ── TCP Scan ──────────────────────────────────────────────────────────
        run_visible_command(scan_data["user_input_tcp_ports"])
        time.sleep(3)

        tcp_output = _run_nmap_tcp(dut_ip)
        scan_data["terminal_output_tcp_ports"] = tcp_output or "No output captured"
        scan_data["terminal_output"] = scan_data["terminal_output_tcp_ports"]

        tcp_shot = os.path.join(
            SCREENSHOT_DIR,
            f"nmap_tcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        pyautogui.screenshot(tcp_shot)
        scan_data["tcp_screenshot"] = tcp_shot
        scan_data["screenshot"] = tcp_shot

        run_visible_command("clear")
        time.sleep(1)

        # ── UDP Scan (SNMP) ───────────────────────────────────────────────────
        run_visible_command(scan_data["user_input_udp_ports"])
        time.sleep(5)

        udp_output = _run_nmap_udp(dut_ip)
        scan_data["terminal_output_udp_ports"] = udp_output or "No output captured"

        udp_shot = os.path.join(
            SCREENSHOT_DIR,
            f"nmap_udp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        pyautogui.screenshot(udp_shot)
        scan_data["udp_screenshot"] = udp_shot

        # ── Detect services ───────────────────────────────────────────────────
        services = _detect_services(tcp_output or "", udp_output or "")
        scan_data.update(services)

    finally:
        exit_terminal()

    return scan_data