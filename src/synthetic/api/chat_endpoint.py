import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn, os, tempfile, socket, subprocess, threading, time
from src.synthetic.gpt_all.chat import OmniModel4All
app = FastAPI()

import asyncio

import logging

def setup_logger():
    logger = logging.getLogger("model_logger")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler("model_api.log")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()



class ChatRequest(BaseModel):
    chat: str
    model_name: str
    router_name: str
    config: dict | None = None

# class ChatRequest(BaseModel):
#     chat: str
#     model_name: str

@app.post('/chat')
async def chat_endpoint(req: ChatRequest):
    try:
        model_name = req.model_name
        omni_model = OmniModel4All(model_name=model_name)
        
        # Nếu send_chat là hàm đồng bộ, gọi trong thread pool:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, omni_model.send_chat, req.chat)
        
        status = "success" if result else "error"
        return {"response ": result, "status": status}
    
    except Exception as e:
        logger.error(f"Exception in chat_endpoint: {e}")
        return {"response ": "", "status": "error", "message": str(e)}




# @app.post("/chat")
# def chat_endpoint(req: ChatRequest):
#     omni_model = OmniModel4All(model_name=req.model_name)
#     result = omni_model.send_chat(req.chat)

#     # handler = PuterChatHandler(req.model_name)
#     # result = handler.send_chat(req.chat)


#     if result and not result.startswith("<Error>"):

#         return {"result": result}
#     else:
#         return {"result": f"<Error> {req.model_name} can not get response"}
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1212)