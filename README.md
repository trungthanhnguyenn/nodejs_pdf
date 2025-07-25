## Run docker compose

```bash
cd nodejs_pdf
docker compose run --rm --interactive --tty beq_pdfcrawler
```

## Create env to convert PDF to TXT

```bash
conda create -n beq_pdfcrawler python=3.10 -y
conda activate beq_pdfcrawler
conda install -c conda-forge poppler pdftotext -y
pip install -r requirements.txt
```

## Convert PDF to TXT
```bash
python -m src.convert.pdf2txt
```
