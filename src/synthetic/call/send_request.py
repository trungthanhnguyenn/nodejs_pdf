import aiohttp
import asyncio
import json
from datasets import load_dataset
from pathlib import Path
from tqdm import tqdm
from dataclasses import dataclass

@dataclass
class DataConfig:
    data_name: str
    split: str
    token_hf: str
    column_name: str
    
@dataclass
class ModelConfig:
    model_name: str
    router_name: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 32768
    stream: bool = False

class ChatDataGenerator:
    def __init__(self, data_config, model_config, system_prompt, output_dir):
        self.data_config = data_config
        self.model_config = model_config
        self.system_prompt = system_prompt.strip()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"[🔄] Loading dataset: {self.data_config.data_name}...")
        self.dataset = load_dataset(
            self.data_config.data_name,
            split=self.data_config.split,
            token=self.data_config.token_hf,
        )

    async def _send_to_api(self, session, context_text):
        prompt = f"{self.system_prompt}\n\n---\n{context_text.strip()}\n---"

        payload = {
            "chat": prompt,
            "model_name": self.model_config.model_name,
            "router_name": self.model_config.router_name,
            "config": {
                "temperature": self.model_config.temperature,
                "top_p": self.model_config.top_p,
                "max_tokens": self.model_config.max_tokens,
                "stream": self.model_config.stream
            }
        }

        try:
            async with session.post("http://localhost:1212/chat", json=payload, timeout=180) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "context": context_text,
                        "prompt": prompt,
                        "response": data.get("response ", ""),
                        "status": data.get("status", "unknown")
                    }
                else:
                    return {"context": context_text, "prompt": prompt, "response": "", "status": "error", "message": f"HTTP {response.status}"}
        except Exception as e:
            return {"context": context_text, "prompt": prompt, "response": "", "status": "error", "message": str(e)}

    async def run(self, start_idx=0, stop_idx=None, save_every=50, max_concurrent=1):
        stop_idx = stop_idx or len(self.dataset)
        results = []
        sem = asyncio.Semaphore(max_concurrent)
        batch_start = start_idx

        async def process(i, session):
            async with sem:
                context = self.dataset[i][self.data_config.column_name]
                result = await self._send_to_api(session, context)
                result["index"] = i
                return result

        async with aiohttp.ClientSession() as session:
            for batch_start in tqdm(range(start_idx, stop_idx, save_every)):
                batch_end = min(batch_start + save_every, stop_idx)
                batch_tasks = [process(i, session) for i in range(batch_start, batch_end)]
                batch_results = await asyncio.gather(*batch_tasks)

                # Sort theo index để đảm bảo đúng thứ tự
                batch_results.sort(key=lambda r: r["index"])

                self._save_batch(batch_results, batch_start, batch_end - 1)

    def _save_batch(self, batch, start_idx, end_idx):
        filename = self.output_dir / f"output_{start_idx}_{end_idx}.jsonl"
        with open(filename, "w", encoding="utf-8") as f:
            for item in batch:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"[💾] Saved batch: {filename}")
