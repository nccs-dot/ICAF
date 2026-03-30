from .excel_parser import parse_oam_excel
from .protocol_verifier import verify_protocols


def process_oam(file_path, dut_ip):
    protocols, df = parse_oam_excel(file_path)

    verified_protocols = verify_protocols(dut_ip, protocols)

    return {
        "raw_protocols": protocols,
        "verified_protocols": verified_protocols,
        "dataframe": df
    }