from src.synthetic.gpt_all.mapping import model_list
import g4f
g4f.debug.logging = True  # Enable debug logging
g4f.debug.version_check = False
from icecream import ic

class OmniModel4All:

    def __init__(self, model_name:str):

        self.model_name = model_name
    
    # def check_model_available(self):

    #     if 'gpt' in self.model_name:
    #         if self.model_name not in model_list['gpt']:
    #             ic(f"Not support {self.model_name}, gpt just support: {model_list['gpt']}")

    #     elif 'gemini' in self.model_name:
    #         if self.model_name not in model_list['gemini']:
    #             ic(f" Not support {self.model_name}, gemini just support: {model_list['gemini']}")

    #     elif 'grok' in self.model_name:
    #         if self.model_name not in model_list['grok']:
    #             ic(" Not support {self.model_name}, grok just support: {model_list['grok']}")

    #     if 'sonar' in self.model_name:
    #         if self.model_name not in model_list['sonar']:
    #             ic(f" Not support {self.model_name}, sonar just support: {model_list['sonar']}")
    #     else:
    #         ic(f"Not support {self.model_name} just support {model_list.keys()}")

            
    def conversasion(self, messages:str):

        return  g4f.ChatCompletion.create(model=g4f.models.gpt_4,
            messages=[{"role": "user", "content":messages}])

             
    def send_chat(self, prompt:str) -> str:

        # Check model

        # self.check_model_available()

        try:

            return self.conversasion(messages=prompt)
        except Exception as e:
            return f"<Error> can not get response {e}"
