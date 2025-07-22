# import json

# with open('VBPL_raw_url.json', 'r', encoding='utf-8') as f:
#     data = json.load(f)

# filtered = [item for item in data if 'luật' in item['title'].lower()]

# with open('urls.txt', 'w', encoding='utf-8') as f:
#     for item in filtered:
#         title = item['title'].strip().replace('\n', ' ')
#         url = item['url'].strip()
#         f.write(f"{title}|||{url}\n")

# print(f'Đã lưu {len(filtered)} URL vào file "urls.txt"')

from huggingface_hub import HfApi
import os

def upload_large_pdf_folder(local_dir: str, repo_id: str):
    """
    Upload thư mục lớn chứa nhiều file (PDF) lên Hugging Face bằng upload_large_folder.
    """
    api = HfApi()

    api.upload_large_folder(
        folder_path=local_dir,
        repo_id=repo_id,
        repo_type="dataset",
        # path_in_repo="",
        allow_patterns=["*.pdf"],  # chỉ upload file .pdf (tùy chọn)
    )

    print(f"[✅] Thư mục '{local_dir}' đã được upload lên https://huggingface.co/datasets/{repo_id}")

# def upload_to_huggingface(local_dir: str, repo_id: str):
#     """
#     Upload toàn bộ thư mục local_dir lên Hugging Face Hub dưới repo_id (kiểu dataset).
    
#     Args:
#         local_dir (str): Đường dẫn thư mục cần upload.
#         repo_id (str): Tên repo trên HF, dạng 'username/repo-name'.
#     """
#     if not os.path.exists(local_dir):
#         raise FileNotFoundError(f"❌ Thư mục '{local_dir}' không tồn tại.")

#     print(f"[INFO] Tạo hoặc kiểm tra repo: {repo_id}")
#     create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)

#     print(f"[INFO] Bắt đầu upload thư mục: {local_dir}")
#     upload_folder(
#         repo_id=repo_id,
#         folder_path=local_dir,
#         repo_type="dataset",
#         path_in_repo="",  # giữ nguyên cấu trúc thư mục
#     )

#     print(f"[✅] Upload hoàn tất lên: https://huggingface.co/datasets/{repo_id}")

if __name__ == "__main__":
    upload_large_pdf_folder(
        local_dir="output",
        repo_id="trungnguyen2331/law-pdf",
    )