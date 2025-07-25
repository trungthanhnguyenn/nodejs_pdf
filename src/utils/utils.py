import os
from tqdm import tqdm
import csv
from huggingface_hub import HfApi, HfFolder, upload_file
from datasets import load_dataset, Dataset, DatasetDict
import sys

system_prompt = r"""
Bạn là một chuyên gia pháp luật có nhiệm vụ **trích xuất thông tin có cấu trúc** từ văn bản pháp luật đã được số hóa (OCR hoặc định dạng văn bản thường).

Yêu cầu:
- Dựa vào phần context bên dưới, hãy điền thông tin vào **hai bảng JSON** với đúng **tên trường và định dạng** như mô tả.
- Nếu **không đủ thông tin** để điền các bảng, hãy trả về **chuỗi duy nhất**: PDF không chứa đủ thông tin để điền vào bảng.
- Tuyệt đối **không trả lời, giải thích hoặc tạo thêm thông tin ngoài context.**
- Chỉ trả về đúng hai bảng JSON hoặc chuỗi đặc biệt trên.
- Không tóm tắt phần "noi_dung" mà phải trả về **toàn bộ** nội dung của văn bản.

------ 🗂️ Bảng 1: Thông tin văn bản pháp luật ------
json
{{
  "so_hieu": "...",                  // Số hiệu văn bản (VD: 01/2023/TT-BGDĐT)
  "loai_vb": "...",                  // Loại văn bản (VD: Thông tư, Nghị định)
  "noi_ban_hanh": "...",            // Cơ quan ban hành (VD: Bộ Tài chính)
  "nguoi_ky": "...",                // Người ký ban hành
  "ngay_ban_hanh": "...",           // Ngày ban hành (YYYY-MM-DD)
  "ngay_hieu_luc": "...",           // Ngày có hiệu lực
  "ngay_cong_bao": "...",           // Ngày công bố
  "so_cong_bao": "...",             // Số Công báo
  "tinh_trang": "...",              // Trạng thái hiệu lực (VD: Còn hiệu lực)
  "tieu_de": "...",                 // Tên văn bản
  "noi_dung": "...",                // Toàn bộ nội dung của văn bản không được tóm tắt
  "linh_vuc": "..."                 // Lĩnh vực (VD: Giáo dục, Y tế)
}}
------ Bảng 2: Văn bản liên quan ------
{{
  "tieu_de": "...",                         // Trùng với tiêu đề văn bản hiện tại
  "vb_duoc_hd": ["..."],                    // Văn bản được hướng dẫn bởi
  "vb_hd": ["..."],                         // Văn bản hướng dẫn cho
  "vb_bi_sua_doi_bo_sung": ["..."],         // Văn bản bị sửa đổi, bổ sung bởi
  "vb_sua_doi_bo_sung": ["..."],            // Văn bản sửa đổi, bổ sung cho
  "vb_duoc_hop_nhat": ["..."],              // Văn bản được hợp nhất vào
  "vb_hop_nhat": ["..."],                   // Văn bản hợp nhất các văn bản khác
  "vb_bi_dinh_chinh": ["..."],              // Văn bản bị đính chính bởi
  "vb_dinh_chinh": ["..."],                 // Văn bản đính chính cho
  "vb_bi_thay_the": ["..."],                // Văn bản bị thay thế bởi
  "vb_thay_the": ["..."],                   // Văn bản thay thế cho
  "vb_duoc_dan_chieu": ["..."],             // Văn bản được dẫn chiếu bởi
  "vb_duoc_can_cu": ["..."],                // Văn bản được căn cứ bởi
  "vb_lien_quan_cung_noi_dung": ["..."]     // Các văn bản liên quan nội dung
}}
"""

human_prompt = "Hãy trích xuất thông tin theo yêu cầu."

def get_filename_without_ext(file_path: str) -> str:
    """
    Get the filename without extension from a file path.
    Example: /path/to/file.pdf -> file
    """
    base = os.path.basename(file_path)
    name, _ = os.path.splitext(base)
    return name

def get_all_env_values():
    keys = [
        "GPT_API_KEY",
        "GPT_MODEL_NAME",
        "GPT_BASE_URL",
        "OPENROUTER_KEY",
        "OPEN_ROUTER_NAME",
        "OPENROUTER_BASE_URL",
        "DEEPSEEK_KEY",
        "DEEPSEEK_MODEL_NAME",
        "DEEPSEEK_BASE_URL",
        "GROQ_KEY",
        "GROQ_MODEL_NAME",
        "GROQ_BASE_URL",
        "NVIDIA_KEY",
        "NVIDIA_NAME",
        "NVIDIA_BASE_URL",
        "GITHUB_KEY",
        "GITHUB_VALUE",
        "GITHUB_MODEL_NAME",
        "GEMINI_KEY",
        "GEMINI_MODEL_NAME"
    ]
    return {key: os.getenv(key) for key in keys}

def make_csv(output_csv, txt_path):
  # Load title from urls.txt
  title_map = {}
  txt_url = "data/input/txt/urls.txt"
  with open(txt_url, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for idx, line in enumerate(lines):
        if '|||' in line:
          raw_title, _ = line.strip().split("|||", 1)
          clean_title = raw_title.replace('/', '_').strip()
          index_name = f"{idx+1:06d}"
          title_map[index_name] = clean_title
  
  mapped_count = 0
  total_count = 0
  
  # Create CSV file
  with open(output_csv, mode="w", newline='', encoding="utf-8") as csvfile:
      writer = csv.DictWriter(
          csvfile,
          fieldnames=["title", "system", "human", "context"],
          quoting=csv.QUOTE_ALL
      )
      writer.writeheader()

      for filename in os.listdir(txt_path):
          if filename.endswith(".txt"):
            total_count += 1
            file_path = os.path.join(txt_path, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                raw_context = f.read().strip().replace('"', '""')  # escape dấu "
                name_without_ext = os.path.splitext(filename)[0]
                
                if name_without_ext in title_map:
                  title = title_map[name_without_ext]
                  mapped_count += 1
                else:
                  title = name_without_ext.replace('/', '_').strip()
                  
                  
                # title = os.path.splitext(filename)[0]

                writer.writerow({
                    "title": title,
                    "system": system_prompt.strip(),
                    "human": human_prompt,
                    "context": raw_context
                })

  print(f"✅ File CSV đã được tạo thành công tại: {output_csv}")
  print(f"🔢 Tổng số file .txt: {total_count}")
  print(f"✅ Đã mapping đúng từ urls.txt: {mapped_count}")
  print(f"⚠️ Chưa mapping được: {total_count - mapped_count}")

def upload(csv_path, repo_id):
  dataset = Dataset.from_csv(csv_path)
  data = DatasetDict({'train': dataset})
  data.push_to_hub(repo_id=repo_id, max_shard_size='150MB')
  
def mapping(pdf_folder, txt_url):
  count = 0
  with open(txt_url, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
  for idx, line in enumerate(lines):
    if '|||' not in line:
      continue
    
    title, _ = line.strip().split("|||", 1)
    clean_title = title.replace('/', '_').strip()
    old_filename = f"{idx+1:06d}.pdf"
    new_filename = f"{clean_title}.pdf"
    
    old_path = os.path.join(pdf_folder, old_filename)
    new_path = os.path.join(pdf_folder, new_filename)
    
    if os.path.exists(old_path):
      try:
        os.rename(old_path, new_path)
        print(f"✅ Đã đổi tên tệp: {old_path} -> {new_path}")
        count += 1
      except Exception as e:
        print(f"❌ Không thể đổi tên tệp: {old_path} -> {new_path}")
        print(e)
    else:
      print(f"❌ Không tìm thấy tệp: {old_path}")
      
def remapping(pdf_folder: str, txt_url: str):
    """
    Đổi lại tên file PDF về dạng index nếu trước đó đã được đổi tên theo văn bản.
    Nếu file vẫn giữ tên gốc theo index thì giữ nguyên.
    """
    count = 0
    with open(txt_url, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for idx, line in enumerate(lines):
        if '|||' not in line:
            continue

        title, _ = line.strip().split("|||", 1)
        clean_title = title.replace('/', '_').strip()
        expected_index_name = f"{idx+1:06d}.pdf"

        current_title_path = os.path.join(pdf_folder, f"{clean_title}.pdf")
        current_index_path = os.path.join(pdf_folder, expected_index_name)

        # Nếu file đang ở dạng tên văn bản => đổi lại
        if os.path.exists(current_title_path):
            try:
                os.rename(current_title_path, current_index_path)
                print(f"🔁 Đã đổi lại: {clean_title}.pdf -> {expected_index_name}")
                count += 1
            except Exception as e:
                print(f"❌ Lỗi khi đổi lại: {clean_title}.pdf -> {expected_index_name}")
                print(e)
        # Nếu đã là file index thì bỏ qua
        elif os.path.exists(current_index_path):
            print(f"✅ Đã đúng tên: {expected_index_name} (giữ nguyên)")
        else:
            print(f"⚠️ Không tìm thấy file tương ứng cho dòng {idx+1}: '{clean_title}.pdf' hoặc '{expected_index_name}'")

    print(f"\n👉 Tổng cộng đã đổi lại {count} file PDF về tên dạng index.")
      
# if __name__ == "__main__":
#   mapping('/home/truongnn/trung/project/law_searching/data/input/pdf', '/home/truongnn/trung/practice/test/urls.txt')
    # remapping('data/input/pdf', '/home/truongnn/trung/practice/test/urls.txt')