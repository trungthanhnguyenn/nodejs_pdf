import os
from tqdm import tqdm
import csv
from datasets import load_dataset, Dataset, DatasetDict
import sys
import pandas as pd

system_prompt = r"""
Bạn là một chuyên gia pháp luật có nhiệm vụ **trích xuất thông tin có cấu trúc** từ văn bản pháp luật đã được số hóa (OCR hoặc định dạng văn bản thường).

Yêu cầu bắt buộc:
- Dựa vào phần `context` bên dưới, hãy điền dữ liệu vào **bảng JSON** đúng theo định dạng và tên trường được chỉ định.
- Nếu **thiếu quá nhiều trường thông tin quan trọng**, hãy trả về chuỗi duy nhất:
  `PDF không chứa đủ thông tin để điền vào bảng.`
- Trả về đối tượng JSON **gốc, không bọc trong chuỗi**.
- Trường `"noi_dung"` phải chứa **toàn bộ nội dung văn bản từ phần **Quốc hiệu Tiêu ngữ trở xuống**, không được rút gọn hoặc mô tả bằng lời.
- Chỉ trả về đúng một trong hai:
  1. Một đối tượng JSON đầy đủ.
  2. Hoặc chuỗi `"PDF không chứa đủ thông tin để điền vào bảng."`

---

Cấu trúc JSON yêu cầu:
{
  "so_hieu": "...",                  // Số hiệu văn bản (VD: 01/2023/TT-BGDĐT)
  "loai_vb": "...",                  // Loại văn bản (VD: Thông tư, Nghị định)
  "noi_ban_hanh": "...",            // Cơ quan ban hành (VD: Bộ Tài chính)
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
"""

human_prompt = "Hãy trích xuất thông tin theo yêu cầu."

class AutoCreateDataRequest():
    def __init__(self, txt_folder, output_csv_new, error_log_path, repo_id, urls_path):
        self.txt_folder = txt_folder
        self.output_csv_new = output_csv_new
        self.error_log_path = error_log_path
        self.repo_id = repo_id
        self.urls_path = urls_path
        # self.hf_csv = hf_csv
        
    def make_new_csv(self):
        # Load all titles from urls.txt
        with open(self.urls_path, mode="r", encoding="utf-8") as f:
            lines = f.readlines()
            titles = [line.split("|||")[0].strip() for line in lines]

        txt_files = [f for f in os.listdir(self.txt_folder) if f.endswith('.txt')]
        error_count = 0

        os.makedirs(os.path.dirname(self.error_log_path), exist_ok=True)

        ##### First, clean the txt folder:
        with open(self.error_log_path, "w", encoding="utf-8") as log_file:
            for filename in tqdm(txt_files, desc="Cleaning TXT files"):
                file_path = os.path.join(self.txt_folder, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if "Đang tải văn bản..." in content:
                            os.remove(file_path)
                            log_file.write(f"Removed empty file: {os.path.splitext(filename)[0]}\n")
                            error_count += 1
                except Exception as e:
                    log_file.write(f"Error processing {filename}: {str(e)}\n")
                    error_count += 1

        # Regenerate file list after cleanup
        txt_files = sorted([f for f in os.listdir(self.txt_folder) if f.endswith('.txt')])
                    
        os.makedirs(os.path.dirname(self.output_csv_new), exist_ok=True)

        ###### Then, create the CSV file:
        with open(self.output_csv_new, mode="w", newline='', encoding="utf-8") as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=["title", "system", "human", "context"],
                quoting=csv.QUOTE_ALL
            )
            writer.writeheader()

            for filename in tqdm(txt_files, desc="Creating CSV"):
                file_path = os.path.join(self.txt_folder, filename)
                try:
                    inx = int(os.path.splitext(filename)[0]) - 1
                    raw_title = titles[inx] if 0 <= inx < len(titles) else f"UNKNOWN_TITLE_{filename}"
                    title = raw_title.replace("/", "_")
                    
                    with open(file_path, "r", encoding="utf-8") as f:
                        raw_context = f.read().strip().replace('"', '""')  # escape dấu "
                    #     title = os.path.splitext(filename)[0]

                        writer.writerow({
                            "title": title,
                            "system": system_prompt.strip(),
                            "human": human_prompt,
                            "context": raw_context
                        })
                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")
                    with open(self.error_log_path, "a", encoding="utf-8") as log_file:
                        log_file.write(f"Error processing {filename}: {str(e)}\n")
                    error_count += 1
        # dataset = Dataset.from_csv(self.output_csv)
        # data = DatasetDict({'train': dataset})
        # data.push_to_hub(repo_id=self.repo_id, max_shard_size='150MB')
                          
    def download_compare_update(self):
        """
        Download the latest dataset from Hugging Face and update the local CSV file.
        """
        dataset = load_dataset(self.repo_id, split='train')
        df = dataset.to_pandas()
        
        df_new = pd.read_csv(self.output_csv_new)
        df_merged = pd.concat([df, df_new], ignore_index=True)
        print(f"Total rows after merging: {len(df_merged)}")
        
        df_merged = df_merged.drop_duplicates(subset=['title'], keep='first')
        print(f"Total rows after removing duplicates: {len(df_merged)}")
        
        # dataset = Dataset.from_pandas(df_merged)
        # DatasetDict({"train": dataset}).push_to_hub(repo_id=self.repo_id, max_shard_size="150MB")
        
        # print(f"Upload new data to Hugging Face: {self.repo_id}")   
  
def check_csv(csv_file: str, index_to_check: int):
  csv.field_size_limit(sys.maxsize)  # ✅ Tăng giới hạn cho ô dữ liệu lớn

  with open(csv_file, mode="r", encoding="utf-8") as f:
      reader = csv.DictReader(f)
      rows = list(reader)

      if index_to_check < len(rows):
          row = rows[index_to_check]
          print(f"🔎 Dòng số {index_to_check}:")
          print(f"📌 Title:\n{row['title']}\n")
          print(f"📌 System:\n{row['system']}\n")
          print(f"📌 Human:\n{row['human']}\n")
          print(f"📌 Context (1000 ký tự đầu):\n{row['context'][:1000]}...\n")
      else:
          print(f"❌ Index {index_to_check} vượt quá số dòng trong CSV ({len(rows)})")

# check_csv("demo.csv", 301)
if __name__ == "__main__":
    # Create a new dataset
    data = AutoCreateDataRequest(
        txt_folder="output/txt",
        output_csv_new="output/csv/demo.csv",
        error_log_path="logs/error/txts_fail.log",
        repo_id="trungnguyen2331/law_extract",
        urls_path="urls.txt",
    )
    data.make_new_csv()
    data.download_compare_update()
