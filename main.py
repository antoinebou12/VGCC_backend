#Libraries
from fastapi import FastAPI, HTTPException
import os
import sys
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.documents import Document
from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv() 

# Load environment variables
api_key = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Initialize ChatGPT instance
llm = ChatOpenAI(openai_api_key=api_key)

# Load content from the local file
file_path = "text.txt"
try:
    with open(file_path, "r", encoding="utf-8") as file:
        text_content = file.read()
except FileNotFoundError: # If the file does not exist, create it
    with open(file_path, "w", encoding="utf-8") as file:
        file.write("sample text content")

# the embeddings prepare the document for vectorization
embeddings = OpenAIEmbeddings(openai_api_key=api_key)

# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter()
documents = text_splitter.split_documents([Document(page_content=text_content)])
vector = FAISS.from_documents(documents, embeddings)

# First we need a prompt that we can pass into an LLM to generate this search query
prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer the user's questions based on the below context:\n\n{context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
])

document_chain = create_stuff_documents_chain(llm, prompt)
retriever = vector.as_retriever()
retrieval_chain = create_retrieval_chain(retriever, document_chain)
#retriever_chain = create_history_aware_retriever(llm, retriever, prompt)
#retrieval_chain = create_retrieval_chain(retriever_chain, document_chain)

chat_history = [HumanMessage(content="Hello"), AIMessage(content="Hello! how can I help you today?")]

# Endpoint to receive user input and return LLM response
@app.post("/llm/response/")
async def llm_response(input_text: str):
    # Get LLM response for user input

    response = retrieval_chain.invoke({
    "chat_history": chat_history,
    "input": input_text
    })
    # Update chat history with the new human query and AI response
    chat_history.append(HumanMessage(content=input_text))
    chat_history.append(AIMessage(content=response["answer"]))

    return {"chat_history": chat_history}

# Endpoint to delete text.txt
@app.delete("/delete-text/")
async def delete_text():
    try:
        os.remove("text.txt")
        return {"message": "text.txt deleted successfully"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="text.txt not found")
    
# Endpoint to create text.txt
@app.post("/create-text/")
async def create_text():
    try:
        with open("text.txt", "w") as text:
            text.write("Valentin is Colombian, he is 22 years old, born in 2001 and is a software engineering student.")
        return {"message": "text.txt created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Additional endpoints can be added as needed

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=8000, reload=True)
