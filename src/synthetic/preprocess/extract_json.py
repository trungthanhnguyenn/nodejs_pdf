import os
import re
import json
from pathlib import Path
from typing import List

def is_valid_response(text: str, index: int, log_file: str) -> bool:
    """
    Kiểm tra phản hồi có hợp lệ hay không. Nếu không hợp lệ, ghi log chi tiết lỗi.
    """
    try:
        # Nếu có markdown block thì lấy nội dung bên trong
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

        # Bước 1: Parse JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            with open(log_file, "a", encoding="utf-8") as log:
                # Kiểm tra xem có phải JSON bị cắt cụt không
                if "Unterminated string" in str(e) or "Expecting" in str(e):
                    log.write(f"Index {index}: Fail at step 'JSON parsing' - JSON truncated or incomplete (error: {str(e)})\n")
                else:
                    log.write(f"Index {index}: Fail at step 'JSON parsing' - Invalid JSON format (error: {str(e)})\n")
                
                # Log thêm thông tin debug
                log.write(f"  -> Text length: {len(text)} characters\n")
                log.write(f"  -> Text ends with: '{text[-50:] if len(text) > 50 else text}'\n")
                log.write(f"  -> Contains opening brace: {'{' in text}\n")
                log.write(f"  -> Contains closing brace: {'}' in text}\n")
            return False
        
        # Bước 2: Kiểm tra dữ liệu có phải là dict không
        if not isinstance(data, dict):
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(f"Index {index}: Fail at step 'Data type validation' - Expected dict, got {type(data).__name__}\n")
            return False
        
        # Bước 3: Kiểm tra các trường bắt buộc
        required_fields = ["so_hieu", "loai_vb", "noi_ban_hanh", "nguoi_ky", "ngay_ban_hanh"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(f"Index {index}: Fail at step 'Field validation' - Missing fields: {', '.join(missing_fields)}\n")
                log.write(f"  -> Available fields: {', '.join(data.keys())}\n")
            return False
        
        # Bước 4: Kiểm tra các trường có giá trị rỗng không
        empty_fields = [field for field in required_fields if not data[field] or str(data[field]).strip() == ""]
        if empty_fields:
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(f"Index {index}: Fail at step 'Field content validation' - Empty fields: {', '.join(empty_fields)}\n")
            return False

        return True

    except Exception as e:
        # Bước 5: Ghi lại lỗi bất ngờ (các trường hợp không xác định)
        with open(log_file, "a", encoding="utf-8") as log:
            log.write(f"Index {index}: Fail at step 'Unexpected error' - {str(e)}\n")
            log.write(f"  -> Exception type: {type(e).__name__}\n")
        return False


def try_repair_json(text: str) -> str:
    """
    Cố gắng sửa chữa JSON bị cắt cụt đơn giản
    """
    text = text.strip()
    
    # Nếu JSON bị thiếu dấu đóng ngoặc
    if text.startswith('{') and not text.endswith('}'):
        # Đếm số dấu { và }
        open_braces = text.count('{')
        close_braces = text.count('}')
        
        if open_braces > close_braces:
            # Thêm dấu đóng ngoặc thiếu
            text += '}' * (open_braces - close_braces)
    
    return text


def is_valid_response_with_repair(text: str, index: int, log_file: str) -> bool:
    """
    Kiểm tra phản hồi có hợp lệ hay không, có thử sửa chữa JSON bị cắt cụt
    """
    # Thử validate JSON gốc trước
    if is_valid_response(text, index, log_file):
        return True
    
    # Nếu fail, thử sửa chữa JSON
    try:
        # Lấy nội dung JSON
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            json_text = match.group(1).strip()
        else:
            json_text = text.strip()
        
        # Thử sửa chữa
        repaired_json = try_repair_json(json_text)
        
        # Thử parse JSON đã sửa
        try:
            data = json.loads(repaired_json)
            
            if isinstance(data, dict):
                required_fields = ["so_hieu", "loai_vb", "noi_ban_hanh", "nguoi_ky", "ngay_ban_hanh"]
                if all(field in data and data[field] and str(data[field]).strip() for field in required_fields):
                    with open(log_file, "a", encoding="utf-8") as log:
                        log.write(f"Index {index}: SUCCESS after JSON repair\n")
                    return True
        except:
            pass
    
    except Exception as e:
        with open(log_file, "a", encoding="utf-8") as log:
            log.write(f"Index {index}: Repair attempt failed - {str(e)}\n")
    
    return False

def merge_jsonl_files(input_dir: str, output_dir: str, log_file: str):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    log_path = Path(log_file)

    output_path.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    merged_records = []
    failed_indices = []

    all_files = sorted(input_path.glob("*.jsonl"), key=lambda p: int(re.findall(r"\d+", p.stem)[0]))

    for file in all_files:
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    index = record.get("index", -1)
                    response_text = record.get("response", "")
                    
                    # Sử dụng hàm có khả năng sửa chữa JSON
                    if is_valid_response_with_repair(response_text, index, log_file):
                        # merged_records.append(record)
                        merged_records.append({"response": response_text, "index": index})
                    else:
                        failed_indices.append(index)
                except Exception as e:
                    with open(log_file, "a", encoding="utf-8") as log:
                        log.write(f"Index {index}: Failed due to record parsing error: {str(e)}\n")
                    continue

    # Gom theo index liền nhau và lưu
    merged_records.sort(key=lambda r: r["index"])
    group = []
    prev_idx = None

    for record in merged_records:
        idx = record["index"]
        if prev_idx is None or idx == prev_idx + 1:
            group.append(record)
        else:
            save_merged_group(group, output_path)
            group = [record]
        prev_idx = idx

    if group:
        save_merged_group(group, output_path)

    # Ghi các index lỗi vào log
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\nSUMMARY: Failed indices: {sorted(set(failed_indices))}\n")
        log.write(f"Total failed: {len(set(failed_indices))}\n")
        log.write(f"Total successful: {len(merged_records)}\n")

def save_merged_group(records: List[dict], output_path: Path):
    start = records[0]["index"]
    end = records[-1]["index"]
    out_file = output_path / f"merged_{start}_{end}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[✅] Saved: {out_file.name} ({len(records)} records)")