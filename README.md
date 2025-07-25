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

## Setup CSV file and update to HF dataset

- For the **first time**, you need to run the function to create the CSV file and upload it to HF dataset (uncomment line 113-115 in `src/synthetic/create_update_dataset.py`)

- You can test the function by uncomment the main function in `src/synthetic/create_update_dataset.py`

- After that, comment out the line 113-115 and run the function again whenever you want to update the dataset.

- Create an `.env` in the root directory using the template below.

```bash
touch .env
echo "HF_TOKEN=your_hf_token" > .env
python -m src.synthetic.create_update_dataset
```

## Run uvicorn server for LLM systhetic data

```bash
bash scripts/run_synthetic_data.sh
```

- You can test the function using main.py file below
- Set the 'data_name' to your repo name that uploaded to Hugging Face in step above
- Run the code in another teminal

```bash
cd nodejs_pdf
python main.py
```