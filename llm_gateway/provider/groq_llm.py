import os
from langchain_groq import ChatGroq
from pathlib import Path
from langchain_core.messages import AIMessage,SystemMessage,HumanMessage
import yaml
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "app/core/config.yml"

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

models = config["llm_provider"]["models"]
#select other models for different capabilities model = models[0],model = models[1],model = models[2],model = models[3],model = models[4]
model = models[3]

def get_model(model_name: str) -> ChatGroq:
    llm = ChatGroq(
        model=model_name,
        api_key=GROQ_API_KEY,
        temperature=0.3,
        max_retries=4,
        max_tokens=3000,
        timeout=15,
    )
    return llm

prompt = """you are a helpful assistant who answer in short paragraph"""

def main(query:str) ->str:
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=query),
    ]
    llm = get_model(model)
    result = llm.invoke(messages)
    return result.content

if __name__ == "__main__":
    query = input("Enter the query: ")
    response = main(query)
    print(response)