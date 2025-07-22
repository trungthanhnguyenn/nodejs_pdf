# Dựa trên image đã cài sẵn Playwright + Chromium
FROM mcr.microsoft.com/playwright:v1.45.0-jammy

WORKDIR /app

# Sao chép project
COPY . .

# Cài Node dependencies
RUN npm install
RUN npx playwright install chromium

# Tạo thư mục output nếu chưa có
RUN mkdir -p /app/output

# Câu lệnh mặc định: chạy script
CMD ["node", "batch_generate_pdf.js"]
