# main.py
import sys
import os
sys.path.append(os.path.abspath("."))
import asyncio
from dotenv import load_dotenv
from src.synthetic.preprocess.extract_json import merge_jsonl_files
from src.synthetic.call.send_request import ChatDataGenerator, DataConfig, ModelConfig

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

HF_TOKEN = os.getenv("HF_TOKEN")

system_prompt=r"""
Bạn là một chuyên gia pháp luật có nhiệm vụ **trích xuất thông tin có cấu trúc** từ văn bản pháp luật đã được số hóa (OCR hoặc định dạng văn bản thường).

Yêu cầu bắt buộc:
- Dựa vào phần `context` bên dưới, hãy điền dữ liệu vào **bảng JSON** đúng theo định dạng và tên trường được chỉ định.
- Nếu **thiếu quá nhiều trường thông tin quan trọng**, hãy trả về chuỗi duy nhất:
  `PDF không chứa đủ thông tin để điền vào bảng.`
- Trả về đối tượng JSON **gốc, không bọc trong chuỗi**.
- Trường `"noi_dung"` PHẢI chứa toàn bộ nội dung gốc từ **“CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM”** đến **hết văn bản**, bao gồm đầy đủ mọi ý chính, đoạn văn, thông tin, không được rút gọn, bỏ sót hay mô tả lại.

- Cho phép định dạng lại **hợp lý** như:
  - Chuẩn hóa xuống dòng hợp lý giữa các đoạn.
  - Loại bỏ khoảng trắng dư thừa, tab, lỗi OCR.
  - Gộp các dòng bị vỡ câu (nếu cùng một ý).
  - Giữ đúng trật tự và logic của văn bản gốc.

- Tuyệt đối KHÔNG được:
  - Bỏ qua bất kỳ đoạn nội dung nào.
  - Tóm tắt, gom cụm hoặc viết lại ý.

- Trường `"noi_dung"` nên được định dạng rõ ràng để thuận tiện cho việc xử lý tiếp theo (ví dụ: chunking hoặc truy vấn pháp lý).

- Chỉ trả về đúng một trong hai:
  1. Một đối tượng JSON đầy đủ với tất cả các trường được điền đúng.
  2. Hoặc chuỗi: `"PDF không chứa đủ thông tin để điền vào bảng."`

---

Cấu trúc JSON yêu cầu:
{
  "so_hieu": "...",                  // Số hiệu văn bản (VD: 01/2023/TT-BGDĐT)
  "loai_vb": "...",                  // Loại văn bản (VD: Thông tư, Nghị định)
  "noi_ban_hanh": "...",            // Nơi ban hành (VD: Bộ Tài chính, các cấp tỉnh thành)
  "nguoi_ky": "...",                // Người ký ban hành
  "ngay_ban_hanh": "...",           // Ngày ban hành (DD/MM/YYYY)
  "ngay_hieu_luc": "...",           // Ngày có hiệu lực (DD/MM/YYYY)
  "ngay_cong_bao": "...",           // Ngày công bố
  "so_cong_bao": "...",             // Số Công báo
  "tinh_trang": "...",              // Trạng thái hiệu lực (VD: Còn hiệu lực)
  "tieu_de": "...",                 // Tên văn bản
  "noi_dung": "...",                // Toàn bộ nội dung của văn bản, không tóm tắt
  "linh_vuc": "..."                 // Lĩnh vực (VD: Giáo dục, Y tế)
}
"Hãy trích xuất thông tin theo yêu cầu."
"""

data_config = DataConfig(
    data_name="your/hf_repo",
    split="train",
    token_hf=HF_TOKEN,
    column_name="context"
)

model_config = ModelConfig(
    model_name="gemini-2.5-pro",
    router_name="default",
    temperature=0.7,
    top_p=0.9,
    max_tokens=32768,
    stream=False
)

generator = ChatDataGenerator(
    data_config=data_config,
    model_config=model_config,
    system_prompt=system_prompt,
    output_dir="output/synthetic_data"
)

# if __name__ == "__main__":
#     asyncio.run(generator.run(start_idx=0, stop_idx=9501, save_every=10, max_concurrent=10))

#   merge_jsonl_files(
#     input_dir="output/synthetic_data",
#     output_dir="output/json_extracted",
#     log_file="output/log/failed_idx.txt"
#   )