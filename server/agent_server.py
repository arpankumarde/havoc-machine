#!/usr/bin/env python3
"""WebSocket server with LangChain support agent using MongoDB knowledge base."""

import os
import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "havoc_machine")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "document_chunks")
MEMORY_COLLECTION_NAME = "agent_memory"
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "openai/gpt-4o-mini"

# Initialize FastAPI
app = FastAPI()

# MongoDB connections
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DB_NAME]
chunks_collection = db[MONGODB_COLLECTION_NAME]
memory_collection = db[MEMORY_COLLECTION_NAME]

# Create indexes for better performance
try:
    chunks_collection.create_index("embedding")  # For vector search
    chunks_collection.create_index("file_path")  # For file lookups
    memory_collection.create_index("session_id")  # For session lookups
    memory_collection.create_index([("session_id", 1), ("timestamp", -1)])  # For sorted queries
    print("✓ Created MongoDB indexes")
except Exception as e:
    print(f"⚠️  Index creation warning: {e}")

# Initialize embeddings
embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base=OPENROUTER_BASE_URL
)

# Active WebSocket connections (session_id -> websocket)
active_connections: Dict[str, WebSocket] = {}


class MongoDBChatMessageHistory(BaseChatMessageHistory):
    """MongoDB-backed chat message history for conversation."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.collection = memory_collection
    
    @property
    def messages(self):
        """Load messages from MongoDB."""
        from langchain_core.messages import HumanMessage, AIMessage
        
        history_docs = list(self.collection.find(
            {'session_id': self.session_id}
        ).sort('timestamp', 1).limit(20))  # Get last 20 messages
        
        messages = []
        for doc in history_docs:
            if doc.get('input'):
                messages.append(HumanMessage(content=doc['input']))
            if doc.get('output'):
                messages.append(AIMessage(content=doc['output']))
        
        return messages
    
    def add_user_message(self, message: str):
        """Add user message to MongoDB."""
        self.collection.insert_one({
            'session_id': self.session_id,
            'timestamp': datetime.utcnow(),
            'input': message,
            'type': 'human'
        })
    
    def add_ai_message(self, message: str):
        """Add AI message to MongoDB."""
        self.collection.insert_one({
            'session_id': self.session_id,
            'timestamp': datetime.utcnow(),
            'output': message,
            'type': 'ai'
        })
    
    def clear(self):
        """Clear all messages for this session."""
        self.collection.delete_many({'session_id': self.session_id})


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude_a = sum(a * a for a in vec1) ** 0.5
    magnitude_b = sum(b * b for b in vec2) ** 0.5
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


class MongoDBRetriever(BaseRetriever):
    """Custom retriever that uses MongoDB embeddings for similarity search."""
    
    def __init__(self, collection, embedding_model, k=5):
        # Store attributes in a way that bypasses Pydantic validation
        super().__init__()
        # Use object.__setattr__ to set attributes directly
        object.__setattr__(self, '_collection', collection)
        object.__setattr__(self, '_embedding_model', embedding_model)
        object.__setattr__(self, '_k', k)
    
    @property
    def collection(self):
        return self._collection
    
    @property
    def embedding_model(self):
        return self._embedding_model
    
    @property
    def k(self):
        return self._k
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Retrieve relevant documents based on query embedding."""
        # Generate query embedding
        query_embedding = self.embedding_model.embed_query(query)
        
        # Get all documents with embeddings (in production, you'd want to limit this)
        all_docs = list(self.collection.find({"embedding": {"$exists": True}}))
        
        # Calculate similarity for each document
        scored_docs = []
        for doc in all_docs:
            doc_embedding = doc.get("embedding", [])
            if doc_embedding and len(doc_embedding) == len(query_embedding):
                similarity = cosine_similarity(query_embedding, doc_embedding)
                scored_docs.append((similarity, doc))
        
        # Sort by similarity and take top k
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_docs = scored_docs[:self.k]
        
        # Convert to LangChain Documents
        documents = []
        for similarity, doc in top_docs:
            documents.append(Document(
                page_content=doc.get("text", ""),
                metadata={
                    "file_name": doc.get("file_name", "Unknown"),
                    "file_path": doc.get("file_path", ""),
                    "chunk_index": doc.get("chunk_index", 0),
                    "similarity": similarity
                }
            ))
        
        return documents
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """Public method to retrieve relevant documents."""
        return self._get_relevant_documents(query)
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """Async version of retrieval."""
        return self._get_relevant_documents(query)
    
    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """Public async method to retrieve relevant documents."""
        return await self._aget_relevant_documents(query)


def create_retriever():
    """Create a vector store retriever from MongoDB embeddings."""
    return MongoDBRetriever(
        collection=chunks_collection,
        embedding_model=embeddings,
        k=5  # Return top 5 most relevant chunks
    )


def create_agent(session_id: str):
    """Create a LangChain agent for a specific session using LangChain 1.0 LCEL."""
    # Create retriever
    retriever = create_retriever()
    
    # Create chat history
    chat_history = MongoDBChatMessageHistory(session_id)
    
    # Create LLM
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0.7,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL
    )
    
    # Create history-aware retriever prompt
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", "Given a chat history and the latest user question "
         "which might reference context in the chat history, formulate a standalone question "
         "which can be understood without the chat history. Do NOT answer the question, "
         "just reformulate it if needed and otherwise return it as is."),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}")
    ])
    
    # Create history-aware retriever using LCEL
    def get_standalone_question(input: dict):
        if input.get("chat_history"):
            contextualize_chain = contextualize_q_prompt | llm | StrOutputParser()
            return contextualize_chain.invoke(input)
        return input["question"]
    
    def retrieve_docs(input: dict):
        question = get_standalone_question(input)
        return retriever.get_relevant_documents(question)
    
    # Create QA prompt
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful support agent with access to a knowledge base. 
Use the following pieces of context from the knowledge base to answer the question.
If you don't know the answer based on the context, say so. Don't make up answers.

Context: {context}"""),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}")
    ])
    
    # Format documents
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    
    # Create RAG chain using LCEL
    def rag_chain_invoke(input: dict):
        # Get documents
        docs = retrieve_docs(input)
        context = format_docs(docs)
        
        # Invoke QA chain
        qa_chain = qa_prompt | llm | StrOutputParser()
        answer = qa_chain.invoke({
            "context": context,
            "question": input["question"],
            "chat_history": input.get("chat_history", [])
        })
        
        # Store docs in result for source tracking
        return {"answer": answer, "source_documents": docs}
    
    rag_chain = RunnablePassthrough() | rag_chain_invoke
    
    return rag_chain, chat_history


@app.get("/")
async def get():
    """Simple HTML page for testing WebSocket connections."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Support Agent WebSocket Test</title>
    </head>
    <body>
        <h1>Support Agent WebSocket Test</h1>
        <div>
            <input type="text" id="sessionId" placeholder="Session ID" value="test-session-1">
            <button onclick="connect()">Connect</button>
            <button onclick="disconnect()">Disconnect</button>
        </div>
        <div>
            <input type="text" id="messageInput" placeholder="Type your question...">
            <button onclick="sendMessage()">Send</button>
        </div>
        <div id="messages" style="margin-top: 20px; border: 1px solid #ccc; padding: 10px; height: 400px; overflow-y: auto;">
        </div>
        <script>
            let ws = null;
            let sessionId = 'test-session-1';
            
            function connect() {
                sessionId = document.getElementById('sessionId').value || 'default-session';
                ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
                
                ws.onopen = () => {
                    addMessage('System', 'Connected to support agent');
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'answer') {
                        addMessage('Agent', data.answer);
                        if (data.sources && data.sources.length > 0) {
                            addMessage('System', `Sources: ${data.sources.length} documents`);
                        }
                    } else if (data.type === 'error') {
                        addMessage('Error', data.message);
                    }
                };
                
                ws.onerror = (error) => {
                    addMessage('Error', 'WebSocket error');
                };
                
                ws.onclose = () => {
                    addMessage('System', 'Disconnected');
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }
            
            function sendMessage() {
                const input = document.getElementById('messageInput');
                if (ws && input.value) {
                    ws.send(JSON.stringify({type: 'query', question: input.value}));
                    addMessage('You', input.value);
                    input.value = '';
                }
            }
            
            function addMessage(sender, message) {
                const messages = document.getElementById('messages');
                const div = document.createElement('div');
                div.innerHTML = `<strong>${sender}:</strong> ${message}`;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }
            
            // Allow Enter key to send
            document.getElementById('messageInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for support agent."""
    await websocket.accept()
    active_connections[session_id] = websocket
    
    # Create agent for this session
    chain, memory = create_agent(session_id)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "welcome",
            "message": f"Connected to support agent. Session: {session_id}",
            "session_id": session_id
        })
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            if data.get("type") == "query":
                question = data.get("question", "")
                
                if not question:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty question"
                    })
                    continue
                
                try:
                    # Get chat history
                    chat_history_messages = memory.messages
                    
                    # Process query through agent (run in thread pool since chain.invoke is sync)
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: chain.invoke({
                            "question": question,
                            "chat_history": chat_history_messages
                        })
                    )
                    
                    # Extract answer and source documents
                    if isinstance(result, dict):
                        answer = result.get("answer", "I couldn't generate an answer.")
                        source_docs = result.get("source_documents", [])
                    else:
                        answer = str(result) if result else "I couldn't generate an answer."
                        source_docs = []
                    
                    # Save to chat history
                    memory.add_user_message(question)
                    memory.add_ai_message(answer)
                    
                    # Format sources
                    sources = []
                    for doc in source_docs:
                        if hasattr(doc, 'metadata') and hasattr(doc, 'page_content'):
                            sources.append({
                                "file": doc.metadata.get("file_name", "Unknown"),
                                "chunk": doc.metadata.get("chunk_index", 0),
                                "text": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                            })
                    
                    # Send response
                    await websocket.send_json({
                        "type": "answer",
                        "answer": answer,
                        "sources": sources,
                        "session_id": session_id
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Error processing query: {str(e)}"
                    })
            
            elif data.get("type") == "clear_memory":
                # Clear conversation memory
                memory.clear()
                await websocket.send_json({
                    "type": "message",
                    "message": "Memory cleared"
                })
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Error in WebSocket connection {session_id}: {e}")
    finally:
        # Clean up
        if session_id in active_connections:
            del active_connections[session_id]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

