import os
import re
import math
import difflib
import ast
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill, Font, Border, Side
from openpyxl.utils import get_column_letter

# -----------------------------------------------------------------------------
# Friendly Dictionaries for Non-Technical Manual Testers
# -----------------------------------------------------------------------------
FRIENDLY_SECTION_NAMES = {
    "Root": "General Report Information",
    "TestLab": "Laboratory Information",
    "TestExecutionDetails": "Test Execution Summary",
    "TestToolInfo": "Test Equipment & Tools",
    "DutInfo": "Device Under Test (DUT) Setup",
    "DutInformation": "Device Under Test (DUT) Setup",
    "PRx": "Power Receiver (PRx) Parameters",
    "PTx": "Power Transmitter (PTx) Parameters",
    "Measurements": "Measurement Data",
    "DigitalSignatureInfo": "Digital Security & Signature",
    "ReportRemark": "Operator Remarks",
    "TestingScope": "Test Cases & Trace Logs"
}

FRIENDLY_FIELD_NAMES = {
    "SchemaVersion": "Schema Version",
    "LabName": "Laboratory Name",
    "LabLocation": "Laboratory Location",
    "LabManager": "Laboratory Manager",
    "TestEngineer": "Test Engineer Name",
    "EMail": "Contact Email Address",
    "Remarks": "General Remarks",
    "ProjectId": "Project Identifier",
    "ReportSequence": "Report Sequence Number",
    "TestScope": "Selected Test Scope List",
    "TestResult": "Overall Test Result",
    "Passed": "Passed Tests Count",
    "Failed": "Failed Tests Count",
    "Inconclusive": "Inconclusive Tests Count",
    "NotRun": "Not Run Tests Count",
    "CreationTime": "Report Creation Date & Time",
    "SpecVersion": "Qi / MPP Specification Version",
    "TestToolManufacturer": "Tool Manufacturer",
    "ModelName": "Hardware Model Name",
    "SerialNumber": "Equipment Serial Number",
    "LastCalibrationDate": "Last Calibration Date",
    "IsCalibrated": "Calibration Status",
    "SoftwareVersion": "Software Version",
    "FirmwareVersion": "Firmware Version",
    "HardwareVersion": "Hardware Version",
    "DutType": "Device Type (PTx / PRx)",
    "BrandName": "DUT Brand Name",
    "MemberCode": "WPC Member Code",
    "ProductName": "Product Commercial Name",
    "PartNumber": "Manufacturer Part Number",
    "QiId": "Qi Registration ID",
    "PowerProfile": "Power Profile (BPP / EPP / MPP)",
    "SpecificationSupported": "Supported Specification Version",
    "PotentialLoadPower": "Potential Load Power (W)",
    "MeasurementName": "Measurement Parameter Name",
    "BaseUnit": "Measurement Base Unit",
    "PacketMnemonic": "Packet Mnemonic Code",
    "PacketDescription": "Packet Description",
    "PacketType": "Packet Type",
    "PacketDuration": "Packet Duration (ms)",
    "RawData": "Raw Packet Payload",
    "OriginOfPacket": "Packet Direction (Tester / DUT)",
    "TimeStamp": "Packet Timestamp",
    "AppliedNOTALs": "Applied NOTALs",
    "TestStartTime": "Test Start Time",
    "TestEndTime": "Test End Time",
    "ManufacturerCode": "Manufacturer Code",
    "IsAmbientTemperatureMeasured": "Ambient Temperature Measured",
    "Temperature": "Ambient Temperature (°C)",
    "Humidity": "Humidity (%)",
    "Pressure": "Atmospheric Pressure (kPa)",
    "DUTGuid": "DUT Unique Identifier (GUID)",
    "FirmwareHash": "Firmware Hash / Checksum",
    "CertId": "Certification ID"
}

FRIENDLY_TYPES = {
    "string": "Text (String)",
    "integer": "Whole Number (Integer)",
    "number": "Decimal / Number",
    "boolean": "True / False (Boolean)",
    "array": "List of Items (Array)",
    "object": "Data Group (Object)"
}

def friendly_sec(s):
    return FRIENDLY_SECTION_NAMES.get(s, s)

def friendly_field(f):
    return FRIENDLY_FIELD_NAMES.get(f, f)

def friendly_type(t):
    if not t:
        return ""
    t_clean = str(t).strip().lower()
    return FRIENDLY_TYPES.get(t_clean, t)

def humanize_enum(field_name, actual_str, allowed):
    field_display = friendly_field(field_name)
    # 1. Letter case mismatch
    actual_lower = actual_str.lower()
    case_matches = [x for x in allowed if str(x).lower() == actual_lower]
    if case_matches:
        correct = case_matches[0]
        return (
            "Letter Case Mismatch",
            f"The parameter '{field_display}' has value '{actual_str}' with incorrect letter casing. The specification requires '{correct}'.",
            f"Change '{actual_str}' to exact casing '{correct}' in the software or firmware export.",
            f"'{correct}' (Exact Casing)",
            actual_str
        )
    # 2. Separator mismatch
    sep_norm = actual_str.replace("_", "-").replace(" ", "-").lower()
    sep_matches = [x for x in allowed if str(x).replace("_", "-").replace(" ", "-").lower() == sep_norm]
    if sep_matches:
        correct = sep_matches[0]
        return (
            "Syntax Separator Mismatch",
            f"The parameter '{field_display}' has value '{actual_str}' using an incorrect separator. The specification requires '{correct}'.",
            f"Update '{actual_str}' to '{correct}' (replace underscore with hyphen).",
            f"'{correct}'",
            actual_str
        )
    # 3. Unit mismatch
    if actual_str in ["MilliWatt", "milliwatt", "mW", "milli-watt"] and "Watt" in allowed:
        return (
            "Measurement Unit Mismatch",
            f"The unit '{actual_str}' is not an accepted base unit. Measurements must be reported in 'Watt'.",
            "Convert values from milliwatts (mW) to watts (W) before exporting the test report.",
            "Watt (Standard Base Unit)",
            actual_str
        )
    # 4. Known common Qi/MPP mnemonic
    if field_name == "PacketMnemonic" and actual_str == "PtxError":
        return (
            "Unrecognized Packet Mnemonic",
            "Found 'PtxError' in packet trace. In Qi/MPP specification, transmitter error packets must be logged with mnemonic 'ERR'.",
            "Update packet decoding to assign standard mnemonic 'ERR' to transmitter error packets.",
            "'ERR' (Standard Error Packet Mnemonic)",
            actual_str
        )
    # 5. Close match via difflib
    close = difflib.get_close_matches(actual_str, [str(x) for x in allowed], n=1, cutoff=0.6)
    if close:
        correct = close[0]
        return (
            "Unrecognized Option",
            f"The value '{actual_str}' is not an approved option for '{field_display}'. Closest match: '{correct}'.",
            f"Verify if '{correct}' was intended, or select an approved option from specification.",
            f"'{correct}'",
            actual_str
        )
    # 6. Fallback
    if len(allowed) <= 5:
        allowed_str = ", ".join(f"'{x}'" for x in allowed)
        return (
            "Unrecognized Option",
            f"The value '{actual_str}' is not an approved option for '{field_display}'. Allowed: {allowed_str}.",
            f"Select one of the approved options: {allowed_str}.",
            f"One of: {allowed_str}",
            actual_str
        )
    else:
        sample = ", ".join(f"'{x}'" for x in allowed[:4])
        return (
            "Unrecognized Option",
            f"The value '{actual_str}' is not a recognized standard option for '{field_display}' ({len(allowed)} options available, e.g. {sample}).",
            "Select an approved option matching specification requirements.",
            f"Standard Option (e.g. {sample})",
            actual_str
        )

def humanize_err(raw_msg, field_name, expected, actual):
    field_display = friendly_field(field_name)
    if "is not one of" in raw_msg:
        match = re.search(r"'([^']+)'\s+is not one of\s+\[(.*)\]", raw_msg, re.DOTALL)
        if match:
            act = match.group(1)
            try:
                allowed = ast.literal_eval(f"[{match.group(2)}]")
                return humanize_enum(field_name, act, allowed)
            except Exception:
                pass
        return ("Invalid Option", f"The value '{actual}' is not an approved option for '{field_display}'.", "Select an approved option.", "Approved Option", str(actual))
    elif "is a required property" in raw_msg or "(Missing)" in field_name:
        return ("Missing Mandatory Field", f"Mandatory parameter '{field_display}' was left blank or omitted.", f"Ensure '{field_display}' is filled before exporting.", "Mandatory Field", "<Missing>")
    elif "is not of type" in raw_msg:
        return ("Incorrect Data Format", f"Incorrect data format for '{field_display}'. Received: '{actual}'.", f"Verify format of '{field_display}'.", str(expected), str(actual))
    elif "was unexpected" in raw_msg or "Additional properties are not allowed" in raw_msg:
        return ("Unrecognized Extra Parameter", f"Parameter '{field_display}' is not part of specification.", f"Remove or rename '{field_display}'.", "Standard Parameter", str(actual))
    else:
        return ("Specification Discrepancy", raw_msg[:120], "Verify against specification guidelines.", str(expected), str(actual))

def parse_text_logs_to_first_format(log_lines):
    general_rows = []
    scope_issues = []
    all_errors = []
    
    current_mode = "GENERAL"
    current_section = "General Report Information"

    idx = 0
    err_counter = 1
    total_lines = len(log_lines)
    while idx < total_lines:
        line = log_lines[idx].rstrip()
        
        if "SECTION : Testing Scope Verification" in line:
            current_mode = "TEST_SCOPE"
            idx += 1
            continue

        if current_mode == "GENERAL":
            stripped = line.strip()
            if not stripped or stripped.startswith("- -") or stripped.startswith("---") or "Schema Compliance Report" in stripped:
                idx += 1
                continue

            # Section header: SECTION: Name
            if "SECTION:" in stripped:
                sec_match = re.search(r"SECTION:\s*([A-Za-z0-9_]+)", stripped)
                if sec_match:
                    raw_sec = sec_match.group(1)
                    current_section = friendly_sec(raw_sec)
                idx += 1
                continue

            # Check [PASS] -- key : val -> type
            pass_top = re.search(r"\[PASS\]\s+--\s+([^:]+)\s*:\s*(.*?)\s*->\s*(.*)", stripped)
            if pass_top:
                k = pass_top.group(1).strip()
                v = pass_top.group(2).strip()
                t = pass_top.group(3).strip()
                general_rows.append({
                    "section": current_section,
                    "field": friendly_field(k),
                    "raw_field": k,
                    "path": f"$.{k}",
                    "expected": friendly_type(t),
                    "actual": v,
                    "status": "PASS",
                    "remarks": "Valid and conforms to specification"
                })
                idx += 1
                continue

            # Check [FAIL] -- key : err
            fail_top = re.search(r"\[FAIL\]\s+--\s+([^:]+)\s*:\s*(.*)", stripped)
            if fail_top:
                k = fail_top.group(1).strip()
                err = fail_top.group(2).strip()
                cat, issue, act, exp_d, act_d = humanize_err(err, k, "Standard Parameter", "<Invalid>")
                general_rows.append({
                    "section": current_section,
                    "field": friendly_field(k),
                    "raw_field": k,
                    "path": f"$.{k}",
                    "expected": exp_d,
                    "actual": act_d,
                    "status": "FAIL",
                    "remarks": f"[{cat}] {issue} Recommended Action: {act}"
                })
                all_errors.append({
                    "index": err_counter,
                    "validator": cat,
                    "json_path": f"$.{k}",
                    "schema_path": f"properties->{k}",
                    "invalid_value": act_d,
                    "expected_rule": exp_d,
                    "message": issue
                })
                err_counter += 1
                idx += 1
                continue

            # Check indented pass: k : val -> type -- Pass
            pass_sub = re.search(r"^([^:]+)\s*:\s*(.*?)\s*->\s*(.*?)\s*--\s*Pass", stripped)
            if pass_sub:
                k = pass_sub.group(1).strip()
                v = pass_sub.group(2).strip()
                t = pass_sub.group(3).strip()
                general_rows.append({
                    "section": current_section,
                    "field": friendly_field(k),
                    "raw_field": k,
                    "path": f"$.{current_section}.{k}",
                    "expected": friendly_type(t),
                    "actual": v,
                    "status": "PASS",
                    "remarks": "Valid and conforms to specification"
                })
                idx += 1
                continue

            # Check indented pass without -> (e.g. TestScope : array -- Pass)
            pass_simple = re.search(r"^([^:]+)\s*:\s*(.*?)\s*--\s*Pass", stripped)
            if pass_simple:
                k = pass_simple.group(1).strip()
                t = pass_simple.group(2).strip()
                general_rows.append({
                    "section": current_section,
                    "field": friendly_field(k),
                    "raw_field": k,
                    "path": f"$.{current_section}.{k}",
                    "expected": friendly_type(t),
                    "actual": "<Configured>",
                    "status": "PASS",
                    "remarks": "Valid and conforms to specification"
                })
                idx += 1
                continue

            # Check indented fail: k: err -- Fail
            fail_sub = re.search(r"^([^:]+)\s*:\s*(.*?)\s*--\s*Fail", stripped)
            if fail_sub:
                k = fail_sub.group(1).strip()
                err = fail_sub.group(2).strip()
                cat, issue, act, exp_d, act_d = humanize_err(err, k, "Standard Parameter", "<Invalid>")
                general_rows.append({
                    "section": current_section,
                    "field": friendly_field(k),
                    "raw_field": k,
                    "path": f"$.{current_section}.{k}",
                    "expected": exp_d,
                    "actual": act_d,
                    "status": "FAIL",
                    "remarks": f"[{cat}] {issue} Recommended Action: {act}"
                })
                all_errors.append({
                    "index": err_counter,
                    "validator": cat,
                    "json_path": f"$.{current_section}.{k}",
                    "schema_path": f"properties->{current_section}->properties->{k}",
                    "invalid_value": act_d,
                    "expected_rule": exp_d,
                    "message": issue
                })
                err_counter += 1
                idx += 1
                continue

            # Check missing: k (Missing): err --- Fail
            missing_sub = re.search(r"^(\S+)\s*\(Missing\)\s*:\s*(.*?)\s*---\s*Fail", stripped)
            if missing_sub:
                k = missing_sub.group(1).strip()
                err = missing_sub.group(2).strip()
                cat, issue, act, exp_d, act_d = humanize_err(err, k, "Mandatory Parameter", "<Missing>")
                general_rows.append({
                    "section": current_section,
                    "field": friendly_field(k),
                    "raw_field": k,
                    "path": f"$.{current_section}.{k}",
                    "expected": exp_d,
                    "actual": "<Missing>",
                    "status": "FAIL",
                    "remarks": f"[{cat}] {issue} Recommended Action: {act}"
                })
                all_errors.append({
                    "index": err_counter,
                    "validator": cat,
                    "json_path": f"$.{current_section}.{k}",
                    "schema_path": f"required->{k}",
                    "invalid_value": "<Missing>",
                    "expected_rule": exp_d,
                    "message": issue
                })
                err_counter += 1
                idx += 1
                continue

            idx += 1

        elif current_mode == "TEST_SCOPE":
            if "Schema Path -- ↓↓" in line:
                idx += 1
                while idx < total_lines and not log_lines[idx].strip():
                    idx += 1
                schema_path = log_lines[idx].strip() if idx < total_lines else ""
                
                while idx < total_lines and "Error Message -- ↓↓" not in log_lines[idx]:
                    idx += 1
                idx += 1
                while idx < total_lines and not log_lines[idx].strip():
                    idx += 1
                err_msg = log_lines[idx].strip() if idx < total_lines else ""

                while idx < total_lines and "Test Cases Affected  -- ↓↓" not in log_lines[idx]:
                    idx += 1
                idx += 1

                tc_list = []
                while idx < total_lines:
                    l = log_lines[idx].strip()
                    if l.startswith("------------------------------"):
                        break
                    tc_match = re.search(r"^\d+\s*\.\s*(.*)", l)
                    if tc_match:
                        tc_list.append(tc_match.group(1).strip())
                    idx += 1

                path_segments = [p for p in schema_path.split("->") if p]
                param_name = path_segments[-1] if path_segments else "Test Parameter"
                friendly_param = friendly_field(param_name)

                match_enum = re.search(r"'([^']+)'\s+is not one of\s+\[(.*)\]", err_msg, re.DOTALL)
                if match_enum:
                    act_val = match_enum.group(1)
                    try:
                        allowed_items = ast.literal_eval(f"[{match_enum.group(2)}]")
                        cat, issue, act, exp_d, act_d = humanize_enum(param_name, act_val, allowed_items)
                    except Exception:
                        cat, issue, act, exp_d, act_d = humanize_err(err_msg, param_name, "Approved Option", act_val)
                else:
                    cat, issue, act, exp_d, act_d = humanize_err(err_msg, param_name, "Standard Specification", "<Non-compliant>")

                friendly_path = " > ".join(friendly_sec(p) if p in FRIENDLY_SECTION_NAMES else friendly_field(p) for p in path_segments)

                scope_issues.append({
                    "param_name": friendly_param,
                    "raw_field": param_name,
                    "schema_path": friendly_path or schema_path,
                    "category": cat,
                    "error_message": issue,
                    "action": act,
                    "expected": exp_d,
                    "actual": act_d,
                    "raw_message": err_msg,
                    "affected_count": len(tc_list),
                    "test_cases": tc_list,
                    "status": "FAIL"
                })

                all_errors.append({
                    "index": err_counter,
                    "validator": cat,
                    "json_path": f"$.TestingScope[*].{param_name}",
                    "schema_path": schema_path,
                    "invalid_value": act_d,
                    "expected_rule": exp_d,
                    "message": f"{issue} (Affects {len(tc_list)} test cases)"
                })
                err_counter += 1
            else:
                idx += 1

    return general_rows, scope_issues, all_errors

def autofit_sheet(ws, min_col_width=12, max_col_width=75, wrap_cols=None, col_width_overrides=None):
    """
    Dynamically adjusts column widths and row heights so that no text is clipped.
    Wrapped columns are assigned generous widths and their rows expand vertically
    up to Excel's 409.0 pt limit.
    """
    if wrap_cols is None:
        wrap_cols = set()
    if col_width_overrides is None:
        col_width_overrides = {}

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        if col_letter in col_width_overrides:
            ws.column_dimensions[col_letter].width = col_width_overrides[col_letter]
            continue

        max_len = 0
        for cell in col:
            if cell.row in [1, 2]:
                continue
            if cell.value is not None:
                lines = str(cell.value).split("\n")
                for l in lines:
                    if len(l) > max_len:
                        max_len = len(l)

        if col_letter in wrap_cols:
            calc_w = min(max(max_len + 4, 36), max_col_width)
        else:
            calc_w = min(max(max_len + 4, min_col_width), max_col_width)

        ws.column_dimensions[col_letter].width = calc_w

    for row in ws.iter_rows():
        row_idx = row[0].row
        if row_idx in [1, 2]:
            continue
        if row_idx == 3:
            ws.row_dimensions[row_idx].height = 26.0
            continue

        max_lines = 1
        for cell in row:
            if cell.value is not None:
                col_letter = get_column_letter(cell.column)
                col_w = ws.column_dimensions[col_letter].width or 20
                val_str = str(cell.value)
                lines = val_str.split("\n")

                is_wrapped = bool(cell.alignment and cell.alignment.wrap_text)
                if is_wrapped:
                    eff_w = max(int(col_w) - 3, 10)
                    total_cell_lines = 0
                    for l in lines:
                        if len(l) <= eff_w:
                            total_cell_lines += 1
                        else:
                            total_cell_lines += math.ceil(len(l) / eff_w)
                    if total_cell_lines > max_lines:
                        max_lines = total_cell_lines
                else:
                    if len(lines) > max_lines:
                        max_lines = len(lines)

        if max_lines > 1:
            calc_h = (max_lines * 17.5) + 6.0
            ws.row_dimensions[row_idx].height = min(calc_h, 409.0)
        else:
            if ws.row_dimensions[row_idx].height is None:
                ws.row_dimensions[row_idx].height = 22.0

def generate_excel_from_text_logs(log_lines, excel_file_path, product="MPP", mode="TPT", timestamp="", txt_filename=""):
    """
    Generates the original 4-sheet Excel report preferred by the user:
    1. Summary Dashboard (Metadata, KPI Cards, Section Breakdown)
    2. Schema Comparison (Field-by-Field verification with friendly names and types)
    3. Testing Scope Violations (Discrepancy categorization, plain English explanation, exact test cases)
    4. All Schema Errors (Complete Draft-7 validation trace with humanized descriptions)
    
    All columns auto-size, wrapped cells expand row heights dynamically up to 409pt,
    and all technical jargon is translated to plain English for manual testers.
    """
    general_rows, scope_issues, all_errors = parse_text_logs_to_first_format(log_lines)

    total_gen = len(general_rows)
    passed_gen = sum(1 for r in general_rows if r['status'] == 'PASS')
    failed_gen = sum(1 for r in general_rows if r['status'] == 'FAIL')
    comp_rate = round(passed_gen / total_gen * 100, 1) if total_gen > 0 else 100.0

    total_scope_issues = len(scope_issues)
    total_affected_tc = sum(s['affected_count'] for s in scope_issues)
    overall_status = "PASS" if (failed_gen == 0 and total_scope_issues == 0) else "FAIL"

    # Section-wise stats
    section_stats = {}
    for r in general_rows:
        sec = r['section']
        if sec not in section_stats:
            section_stats[sec] = {'total': 0, 'passed': 0, 'failed': 0}
        section_stats[sec]['total'] += 1
        if r['status'] == 'PASS':
            section_stats[sec]['passed'] += 1
        else:
            section_stats[sec]['failed'] += 1

    if scope_issues:
        section_stats['Test Cases & Trace Logs'] = {
            'total': total_affected_tc,
            'passed': 0,
            'failed': total_affected_tc,
            'status': 'FAIL'
        }

    wb = Workbook()

    # Sheet 1: Summary Dashboard
    ws_summary = wb.active
    ws_summary.title = "Summary Dashboard"
    ws_summary.views.sheetView[0].showGridLines = True

    # Sheet 2: Schema Comparison
    ws_general = wb.create_sheet(title="Schema Comparison")
    ws_general.views.sheetView[0].showGridLines = True

    # Sheet 3: Testing Scope Violations
    ws_scope = wb.create_sheet(title="Testing Scope Violations")
    ws_scope.views.sheetView[0].showGridLines = True

    # Sheet 4: All Schema Errors
    ws_errors = wb.create_sheet(title="All Schema Errors")
    ws_errors.views.sheetView[0].showGridLines = True

    font_family = "Segoe UI"
    f_banner = Font(name=font_family, size=15, bold=True, color="FFFFFF")
    f_subbanner = Font(name=font_family, size=10, italic=True, color="D9E1F2")
    f_sec_header = Font(name=font_family, size=11, bold=True, color="FFFFFF")
    f_tbl_header = Font(name=font_family, size=10, bold=True, color="FFFFFF")
    f_data = Font(name=font_family, size=10, color="000000")
    f_data_bold = Font(name=font_family, size=10, bold=True, color="000000")
    f_mono = Font(name="Consolas", size=9, color="1F3864")
    f_pass = Font(name=font_family, size=10, bold=True, color="006100")
    f_fail = Font(name=font_family, size=10, bold=True, color="9C0006")

    fill_midnight = PatternFill(start_color="0F2537", end_color="0F2537", fill_type="solid")
    fill_navy = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    fill_slate = PatternFill(start_color="2C4D75", end_color="2C4D75", fill_type="solid")
    fill_soft_blue = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    fill_even = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_odd = PatternFill(start_color="F7F9FC", end_color="F7F9FC", fill_type="solid")
    fill_pass = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    fill_fail = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    thin_side = Side(style='thin', color="D9D9D9")
    border_thin = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    # -------------------------------------------------------------
    # SHEET 1: Summary Dashboard
    # -------------------------------------------------------------
    ws_summary.merge_cells("A1:G1")
    ws_summary["A1"] = "GRL JSON SCHEMA COMPLIANCE REPORT"
    ws_summary["A1"].font = f_banner
    ws_summary["A1"].fill = fill_midnight
    ws_summary["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_summary.row_dimensions[1].height = 38

    ws_summary.merge_cells("A2:G2")
    ws_summary["A2"] = "Verification of Software Test Report Output Against Reference Draft-7 Schema"
    ws_summary["A2"].font = f_subbanner
    ws_summary["A2"].fill = fill_slate
    ws_summary["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws_summary.row_dimensions[2].height = 22

    ws_summary.merge_cells("A4:C4")
    ws_summary["A4"] = "REPORT METADATA"
    ws_summary["A4"].font = f_tbl_header
    ws_summary["A4"].fill = fill_navy
    ws_summary["A4"].alignment = Alignment(horizontal="center", vertical="center")

    ws_summary.merge_cells("E4:G4")
    ws_summary["E4"] = "COMPLIANCE SUMMARY KPI"
    ws_summary["E4"].font = f_tbl_header
    ws_summary["E4"].fill = fill_navy
    ws_summary["E4"].alignment = Alignment(horizontal="center", vertical="center")
    ws_summary.row_dimensions[4].height = 24

    meta_items = [
        ("Product", product),
        ("Mode", mode),
        ("Report Date", timestamp),
        ("Inspected Report", txt_filename or "Test Report JSON"),
        ("Reference Specification", "JsonSchema.json"),
        ("Overall Status", overall_status)
    ]
    for idx, (lbl, val) in enumerate(meta_items, 5):
        ws_summary[f"A{idx}"] = lbl
        ws_summary[f"A{idx}"].font = f_data_bold
        ws_summary[f"A{idx}"].fill = fill_soft_blue
        ws_summary[f"A{idx}"].border = border_thin
        ws_summary.merge_cells(f"B{idx}:C{idx}")
        ws_summary[f"B{idx}"] = str(val)
        ws_summary[f"B{idx}"].font = f_data
        ws_summary[f"B{idx}"].border = border_thin
        ws_summary[f"C{idx}"].border = border_thin
        if lbl == "Overall Status":
            ws_summary[f"B{idx}"].alignment = Alignment(horizontal="center", vertical="center")
            if val == "PASS":
                ws_summary[f"B{idx}"].font = f_pass
                ws_summary[f"B{idx}"].fill = fill_pass
            else:
                ws_summary[f"B{idx}"].font = f_fail
                ws_summary[f"B{idx}"].fill = fill_fail
        ws_summary.row_dimensions[idx].height = 22

    kpi_items = [
        ("General Fields Checked", total_gen, "INFO"),
        ("General Fields Passed", passed_gen, "PASS"),
        ("General Fields Failed", failed_gen, "FAIL" if failed_gen > 0 else "PASS"),
        ("General Compliance Rate", f"{comp_rate}%", "PASS" if comp_rate == 100 else "FAIL"),
        ("TestingScope Violation Types", total_scope_issues, "FAIL" if total_scope_issues > 0 else "PASS"),
        ("Affected Test Cases", total_affected_tc, "FAIL" if total_affected_tc > 0 else "PASS"),
    ]
    for idx, (lbl, val, stat) in enumerate(kpi_items, 5):
        ws_summary[f"E{idx}"] = lbl
        ws_summary[f"E{idx}"].font = f_data_bold
        ws_summary[f"E{idx}"].fill = fill_soft_blue
        ws_summary[f"E{idx}"].border = border_thin
        ws_summary.merge_cells(f"F{idx}:G{idx}")
        ws_summary[f"F{idx}"] = str(val)
        ws_summary[f"F{idx}"].alignment = Alignment(horizontal="center", vertical="center")
        ws_summary[f"F{idx}"].border = border_thin
        ws_summary[f"G{idx}"].border = border_thin
        if stat == "PASS":
            ws_summary[f"F{idx}"].font = f_pass
            ws_summary[f"F{idx}"].fill = fill_pass
        elif stat == "FAIL":
            ws_summary[f"F{idx}"].font = f_fail
            ws_summary[f"F{idx}"].fill = fill_fail
        else:
            ws_summary[f"F{idx}"].font = f_data_bold
            ws_summary[f"F{idx}"].fill = fill_even

    # Section-Wise Table
    ws_summary.merge_cells("A12:G12")
    ws_summary["A12"] = "SECTION-WISE VERIFICATION BREAKDOWN"
    ws_summary["A12"].font = f_sec_header
    ws_summary["A12"].fill = fill_slate
    ws_summary["A12"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_summary.row_dimensions[12].height = 26

    sec_headers = ["S.No", "Section Name", "Fields Evaluated", "Passed", "Failed", "Compliance Rate", "Section Status"]
    cols = ["A", "B", "C", "D", "E", "F", "G"]
    for c, h in zip(cols, sec_headers):
        cell = ws_summary[f"{c}13"]
        cell.value = h
        cell.font = f_tbl_header
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin
    ws_summary.row_dimensions[13].height = 24

    curr_row = 14
    for s_idx, (sec_name, stats) in enumerate(section_stats.items(), 1):
        fill = fill_even if curr_row % 2 == 0 else fill_odd
        tot = stats.get('total', 0)
        psd = stats.get('passed', 0)
        fld = stats.get('failed', 0)
        crate = f"{round(psd / tot * 100, 1)}%" if tot > 0 else "100.0%"
        status = stats.get('status', 'PASS' if fld == 0 else 'FAIL')

        ws_summary[f"A{curr_row}"] = s_idx
        ws_summary[f"A{curr_row}"].alignment = Alignment(horizontal="center")
        ws_summary[f"B{curr_row}"] = sec_name
        ws_summary[f"B{curr_row}"].alignment = Alignment(horizontal="left")
        ws_summary[f"C{curr_row}"] = tot
        ws_summary[f"C{curr_row}"].alignment = Alignment(horizontal="center")
        ws_summary[f"D{curr_row}"] = psd
        ws_summary[f"D{curr_row}"].alignment = Alignment(horizontal="center")
        ws_summary[f"E{curr_row}"] = fld
        ws_summary[f"E{curr_row}"].alignment = Alignment(horizontal="center")
        ws_summary[f"F{curr_row}"] = crate
        ws_summary[f"F{curr_row}"].alignment = Alignment(horizontal="center")
        ws_summary[f"G{curr_row}"] = status
        ws_summary[f"G{curr_row}"].alignment = Alignment(horizontal="center")

        for c in cols:
            cell = ws_summary[f"{c}{curr_row}"]
            cell.border = border_thin
            cell.font = f_data
            cell.fill = fill

        if status == "PASS":
            ws_summary[f"G{curr_row}"].font = f_pass
            ws_summary[f"G{curr_row}"].fill = fill_pass
        else:
            ws_summary[f"G{curr_row}"].font = f_fail
            ws_summary[f"G{curr_row}"].fill = fill_fail
        ws_summary.row_dimensions[curr_row].height = 20
        curr_row += 1

    autofit_sheet(ws_summary, min_col_width=14, max_col_width=45, col_width_overrides={"A": 16, "B": 36, "C": 16, "D": 12, "E": 28, "F": 16, "G": 18})

    # -------------------------------------------------------------
    # SHEET 2: Schema Comparison (General Fields)
    # -------------------------------------------------------------
    ws_general.freeze_panes = 'A4'
    ws_general.merge_cells("A1:H1")
    ws_general["A1"] = "General Schema Compliance Details (Non-TestingScope Properties)"
    ws_general["A1"].font = f_banner
    ws_general["A1"].fill = fill_midnight
    ws_general["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_general.row_dimensions[1].height = 36

    ws_general.merge_cells("A2:H2")
    ws_general["A2"] = "Detailed comparison of JSON properties against defined data types, enums, formats, and required constraints"
    ws_general["A2"].font = f_subbanner
    ws_general["A2"].fill = fill_slate
    ws_general["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws_general.row_dimensions[2].height = 22

    g_headers = ["S.No", "Section", "Field Name", "JSON Path", "Expected Schema Rule", "Actual Value in JSON", "Status", "Validation Remarks & Recommended Action"]
    g_cols = ["A", "B", "C", "D", "E", "F", "G", "H"]
    for c, h in zip(g_cols, g_headers):
        cell = ws_general[f"{c}3"]
        cell.value = h
        cell.font = f_tbl_header
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin
    ws_general.row_dimensions[3].height = 26

    for idx, row in enumerate(general_rows, 4):
        fill = fill_even if idx % 2 == 0 else fill_odd
        ws_general[f"A{idx}"] = idx - 3
        ws_general[f"A{idx}"].alignment = Alignment(horizontal="center", vertical="top")
        ws_general[f"B{idx}"] = row['section']
        ws_general[f"B{idx}"].alignment = Alignment(horizontal="left", vertical="top")
        ws_general[f"C{idx}"] = row['field']
        ws_general[f"C{idx}"].alignment = Alignment(horizontal="left", vertical="top")
        ws_general[f"C{idx}"].font = f_data_bold
        ws_general[f"D{idx}"] = row['path']
        ws_general[f"D{idx}"].alignment = Alignment(horizontal="left", vertical="top")
        ws_general[f"D{idx}"].font = f_mono
        ws_general[f"E{idx}"] = row['expected']
        ws_general[f"E{idx}"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        ws_general[f"F{idx}"] = str(row['actual'])
        ws_general[f"F{idx}"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        ws_general[f"G{idx}"] = row['status']
        ws_general[f"G{idx}"].alignment = Alignment(horizontal="center", vertical="top")
        ws_general[f"H{idx}"] = row['remarks']
        ws_general[f"H{idx}"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

        for c in g_cols:
            cell = ws_general[f"{c}{idx}"]
            cell.border = border_thin
            if c != "C" and c != "D":
                cell.font = f_data
            cell.fill = fill

        if row['status'] == "PASS":
            ws_general[f"G{idx}"].font = f_pass
            ws_general[f"G{idx}"].fill = fill_pass
        else:
            ws_general[f"G{idx}"].font = f_fail
            ws_general[f"G{idx}"].fill = fill_fail

    autofit_sheet(ws_general, min_col_width=12, max_col_width=75, wrap_cols={"E", "F", "H"})

    # -------------------------------------------------------------
    # SHEET 3: Testing Scope Violations
    # -------------------------------------------------------------
    ws_scope.freeze_panes = 'A4'
    ws_scope.merge_cells("A1:H1")
    ws_scope["A1"] = "Testing Scope Schema Violations"
    ws_scope["A1"].font = f_banner
    ws_scope["A1"].fill = fill_midnight
    ws_scope["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_scope.row_dimensions[1].height = 36

    ws_scope.merge_cells("A2:H2")
    ws_scope["A2"] = "Schema discrepancies and missing mandatory properties across test cases and execution logs"
    ws_scope["A2"].font = f_subbanner
    ws_scope["A2"].fill = fill_slate
    ws_scope["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws_scope.row_dimensions[2].height = 22

    s_headers = ["Issue #", "Parameter / Schema Feature", "Plain-English Problem Description", "What Specification Requires", "Found In Report", "Affected Count", "Affected Test Cases", "Status"]
    s_cols = ["A", "B", "C", "D", "E", "F", "G", "H"]
    for c, h in zip(s_cols, s_headers):
        cell = ws_scope[f"{c}3"]
        cell.value = h
        cell.font = f_tbl_header
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin
    ws_scope.row_dimensions[3].height = 26

    if not scope_issues:
        ws_scope.merge_cells("A4:H4")
        ws_scope["A4"] = "✓ No schema violations detected in TestingScope. All test cases comply with schema."
        ws_scope["A4"].font = f_pass
        ws_scope["A4"].fill = fill_pass
        ws_scope["A4"].alignment = Alignment(horizontal="center", vertical="center")
        ws_scope.row_dimensions[4].height = 32
    else:
        for idx, issue in enumerate(scope_issues, 4):
            fill = fill_even if idx % 2 == 0 else fill_odd
            ws_scope[f"A{idx}"] = idx - 3
            ws_scope[f"A{idx}"].alignment = Alignment(horizontal="center", vertical="top")
            ws_scope[f"B{idx}"] = issue['param_name']
            ws_scope[f"B{idx}"].alignment = Alignment(horizontal="left", vertical="top")
            ws_scope[f"B{idx}"].font = f_data_bold
            ws_scope[f"C{idx}"] = issue['error_message']
            ws_scope[f"C{idx}"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws_scope[f"D{idx}"] = issue['expected']
            ws_scope[f"D{idx}"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws_scope[f"E{idx}"] = issue['actual']
            ws_scope[f"E{idx}"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws_scope[f"F{idx}"] = issue['affected_count']
            ws_scope[f"F{idx}"].alignment = Alignment(horizontal="center", vertical="top")
            ws_scope[f"F{idx}"].font = f_data_bold

            tc_display = issue['test_cases'][:10]
            tc_text = "\n".join(f"{i+1}. {tc}" for i, tc in enumerate(tc_display))
            if len(issue['test_cases']) > 10:
                tc_text += f"\n... and {len(issue['test_cases']) - 10} more test cases"

            ws_scope[f"G{idx}"] = tc_text
            ws_scope[f"G{idx}"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws_scope[f"H{idx}"] = issue['status']
            ws_scope[f"H{idx}"].alignment = Alignment(horizontal="center", vertical="top")

            for c in s_cols:
                cell = ws_scope[f"{c}{idx}"]
                cell.border = border_thin
                if c not in ["B", "F"]:
                    cell.font = f_data
                cell.fill = fill

            ws_scope[f"H{idx}"].font = f_fail
            ws_scope[f"H{idx}"].fill = fill_fail

    autofit_sheet(ws_scope, min_col_width=12, max_col_width=75, wrap_cols={"C", "D", "E", "G"})

    # -------------------------------------------------------------
    # SHEET 4: All Schema Errors
    # -------------------------------------------------------------
    ws_errors.freeze_panes = 'A4'
    ws_errors.merge_cells("A1:G1")
    ws_errors["A1"] = "Complete Draft-7 Schema Validation Error Trace"
    ws_errors["A1"].font = f_banner
    ws_errors["A1"].fill = fill_midnight
    ws_errors["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_errors.row_dimensions[1].height = 36

    ws_errors.merge_cells("A2:G2")
    ws_errors["A2"] = "Complete low-level validation error sequence and diagnosis"
    ws_errors["A2"].font = f_subbanner
    ws_errors["A2"].fill = fill_slate
    ws_errors["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws_errors.row_dimensions[2].height = 22

    e_headers = ["Error #", "Validator / Rule Type", "JSON Path", "Schema Path", "Invalid Value", "Expected / Rule", "Plain-English Error Description"]
    e_cols = ["A", "B", "C", "D", "E", "F", "G"]
    for c, h in zip(e_cols, e_headers):
        cell = ws_errors[f"{c}3"]
        cell.value = h
        cell.font = f_tbl_header
        cell.fill = fill_navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin
    ws_errors.row_dimensions[3].height = 26

    if not all_errors:
        ws_errors.merge_cells("A4:G4")
        ws_errors["A4"] = "✓ No validation errors detected. JSON output is 100% compliant with Draft-7 Schema."
        ws_errors["A4"].font = f_pass
        ws_errors["A4"].fill = fill_pass
        ws_errors["A4"].alignment = Alignment(horizontal="center", vertical="center")
        ws_errors.row_dimensions[4].height = 32
    else:
        for idx, err in enumerate(all_errors[:1000], 4):
            fill = fill_even if idx % 2 == 0 else fill_odd
            ws_errors[f"A{idx}"] = err['index']
            ws_errors[f"A{idx}"].alignment = Alignment(horizontal="center", vertical="top")
            ws_errors[f"B{idx}"] = err['validator']
            ws_errors[f"B{idx}"].alignment = Alignment(horizontal="center", vertical="top")
            ws_errors[f"B{idx}"].font = f_data_bold
            ws_errors[f"C{idx}"] = err['json_path']
            ws_errors[f"C{idx}"].alignment = Alignment(horizontal="left", vertical="top")
            ws_errors[f"C{idx}"].font = f_mono
            ws_errors[f"D{idx}"] = err['schema_path']
            ws_errors[f"D{idx}"].alignment = Alignment(horizontal="left", vertical="top")
            ws_errors[f"E{idx}"] = err['invalid_value']
            ws_errors[f"E{idx}"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws_errors[f"F{idx}"] = err['expected_rule']
            ws_errors[f"F{idx}"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            ws_errors[f"G{idx}"] = err['message']
            ws_errors[f"G{idx}"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

            for c in e_cols:
                cell = ws_errors[f"{c}{idx}"]
                cell.border = border_thin
                if c != "B" and c != "C":
                    cell.font = f_data
                cell.fill = fill

    autofit_sheet(ws_errors, min_col_width=12, max_col_width=75, wrap_cols={"E", "F", "G"})

    os.makedirs(os.path.dirname(excel_file_path), exist_ok=True)
    wb.save(excel_file_path)
    print(f"Successfully generated reverted 4-sheet Excel report: {excel_file_path}")
    return excel_file_path

def generate_excel_report(log_lines, excel_file_path, product="MPP", mode="TPT", timestamp="", txt_filename=""):
    """
    Backward-compatible alias for generate_excel_from_text_logs.
    """
    return generate_excel_from_text_logs(log_lines, excel_file_path, product, mode, timestamp, txt_filename)
