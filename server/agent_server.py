#!/usr/bin/env python3

import os
import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "havoc_machine")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "document_chunks")
MEMORY_COLLECTION_NAME = "agent_memory"
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "openai/gpt-4o-mini"

app = FastAPI()

# set all cors to *
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DB_NAME]
chunks_collection = db[MONGODB_COLLECTION_NAME]
memory_collection = db[MEMORY_COLLECTION_NAME]
groups_collection = db["group"]

try:
    chunks_collection.create_index("embedding")
    chunks_collection.create_index("file_path")
    memory_collection.create_index("session_id")
    memory_collection.create_index([("session_id", 1), ("timestamp", -1)])
    groups_collection.create_index("group_id", unique=True)
    groups_collection.create_index("created_at")
    print("Created MongoDB indexes")
except Exception as e:
    print(f"Index creation warning: {e}")

embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base=OPENROUTER_BASE_URL
)

active_connections: Dict[str, WebSocket] = {}


class MongoDBChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.collection = memory_collection
    
    @property
    def messages(self):
        from langchain_core.messages import HumanMessage, AIMessage
        
        history_docs = list(self.collection.find(
            {'session_id': self.session_id}
        ).sort('timestamp', 1).limit(20))
        
        messages = []
        for doc in history_docs:
            if doc.get('input'):
                messages.append(HumanMessage(content=doc['input']))
            if doc.get('output'):
                messages.append(AIMessage(content=doc['output']))
        
        return messages
    
    def add_user_message(self, message: str):
        self.collection.insert_one({
            'session_id': self.session_id,
            'timestamp': datetime.utcnow(),
            'input': message,
            'type': 'human'
        })
    
    def add_ai_message(self, message: str):
        self.collection.insert_one({
            'session_id': self.session_id,
            'timestamp': datetime.utcnow(),
            'output': message,
            'type': 'ai'
        })
    
    def clear(self):
        self.collection.delete_many({'session_id': self.session_id})


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude_a = sum(a * a for a in vec1) ** 0.5
    magnitude_b = sum(b * b for b in vec2) ** 0.5
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


class MongoDBRetriever(BaseRetriever):
    def __init__(self, collection, embedding_model, k=5):
        super().__init__()
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
        query_embedding = self.embedding_model.embed_query(query)
        all_docs = list(self.collection.find({"embedding": {"$exists": True}}))
        
        scored_docs = []
        for doc in all_docs:
            doc_embedding = doc.get("embedding", [])
            if doc_embedding and len(doc_embedding) == len(query_embedding):
                similarity = cosine_similarity(query_embedding, doc_embedding)
                scored_docs.append((similarity, doc))
        
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_docs = scored_docs[:self.k]
        
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
        return self._get_relevant_documents(query)
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        return self._get_relevant_documents(query)
    
    async def aget_relevant_documents(self, query: str) -> List[Document]:
        return await self._aget_relevant_documents(query)


def create_retriever():
    return MongoDBRetriever(
        collection=chunks_collection,
        embedding_model=embeddings,
        k=5
    )


def create_agent(session_id: str):
    retriever = create_retriever()
    chat_history = MongoDBChatMessageHistory(session_id)
    
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=0.7,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL
    )
    
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", "Given a chat history and the latest user question "
         "which might reference context in the chat history, formulate a standalone question "
         "which can be understood without the chat history. Do NOT answer the question, "
         "just reformulate it if needed and otherwise return it as is."),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}")
    ])
    
    def get_standalone_question(input: dict):
        if input.get("chat_history"):
            contextualize_chain = contextualize_q_prompt | llm | StrOutputParser()
            return contextualize_chain.invoke(input)
        return input["question"]
    
    def retrieve_docs(input: dict):
        question = get_standalone_question(input)
        return retriever.get_relevant_documents(question)
    
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful support agent with access to a knowledge base. 
Use the following pieces of context from the knowledge base to answer the question.
If you don't know the answer based on the context, say so. Don't make up answers.

Context: {context}"""),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}")
    ])
    
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    
    def rag_chain_invoke(input: dict):
        docs = retrieve_docs(input)
        context = format_docs(docs)
        
        qa_chain = qa_prompt | llm | StrOutputParser()
        answer = qa_chain.invoke({
            "context": context,
            "question": input["question"],
            "chat_history": input.get("chat_history", [])
        })
        
        return {"answer": answer, "source_documents": docs}
    
    rag_chain = RunnablePassthrough() | rag_chain_invoke
    
    return rag_chain, chat_history


@app.get("/")
async def get():
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
    await websocket.accept()
    active_connections[session_id] = websocket
    
    chain, memory = create_agent(session_id)
    
    try:
        await websocket.send_json({
            "type": "welcome",
            "message": f"Connected to support agent. Session: {session_id}",
            "session_id": session_id
        })
        
        while True:
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
                    chat_history_messages = memory.messages
                    
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: chain.invoke({
                            "question": question,
                            "chat_history": chat_history_messages
                        })
                    )
                    
                    if isinstance(result, dict):
                        answer = result.get("answer", "I couldn't generate an answer.")
                        source_docs = result.get("source_documents", [])
                    else:
                        answer = str(result) if result else "I couldn't generate an answer."
                        source_docs = []
                    
                    memory.add_user_message(question)
                    memory.add_ai_message(answer)
                    
                    sources = []
                    for doc in source_docs:
                        if hasattr(doc, 'metadata') and hasattr(doc, 'page_content'):
                            sources.append({
                                "file": doc.metadata.get("file_name", "Unknown"),
                                "chunk": doc.metadata.get("chunk_index", 0),
                                "text": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                            })
                    
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
        if session_id in active_connections:
            del active_connections[session_id]


# Pydantic models for API requests
class ParallelAdversarialRequest(BaseModel):
    websocket_url: str
    parallel_executions: int
    duration_minutes: float
    adversarial_model: Optional[str] = None
    judge_model: Optional[str] = None


class ParallelAdversarialResponse(BaseModel):
    group_id: str
    session_ids: List[str]
    status: str
    message: str


# Background task storage
running_tasks: Dict[str, asyncio.Task] = {}


async def run_parallel_adversarial_background(
    websocket_url: str,
    parallel_executions: int,
    duration_minutes: float,
    group_id: str,
    adversarial_model: Optional[str] = None,
    judge_model: Optional[str] = None
):
    """Run parallel adversarial testing in the background"""
    try:
        from parallel_adversarial import run_parallel_adversarial
        
        result = await run_parallel_adversarial(
            websocket_base_url=websocket_url,
            parallel_executions=parallel_executions,
            duration_minutes=duration_minutes,
            adversarial_model=adversarial_model,
            judge_model=judge_model,
            group_id=group_id
        )
        
        print(f"✅ Parallel adversarial test completed for group {group_id}")
        print(f"   Session IDs: {result['session_ids']}")
        print(f"   Reports saved: {result['consolidated_report_paths']}")
        
        # Update group document with report URLs
        report_urls = result.get('consolidated_report_paths', {})
        update_data = {
            "status": "completed",
            "completed_at": datetime.utcnow(),
            "report_urls": {
                "markdown": report_urls.get("markdown"),
                "json": report_urls.get("json")
            }
        }
        groups_collection.update_one(
            {"group_id": group_id},
            {"$set": update_data}
        )
        
    except Exception as e:
        print(f"❌ Error in parallel adversarial test for group {group_id}: {e}")
        import traceback
        traceback.print_exc()
        
        # Update group document with error status
        groups_collection.update_one(
            {"group_id": group_id},
            {"$set": {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow()
            }}
        )
    finally:
        # Remove task from running tasks
        if group_id in running_tasks:
            del running_tasks[group_id]


@app.post("/api/adversarial/parallel", response_model=ParallelAdversarialResponse)
async def start_parallel_adversarial(request: ParallelAdversarialRequest, background_tasks: BackgroundTasks):
    """
    Start parallel adversarial testing with multiple agents.
    
    This endpoint spins up multiple adversarial agents in parallel, each focusing on different topics
    to better exploit vulnerabilities. Agents run in the background and generate a consolidated
    report when complete.
    
    Parameters:
    - websocket_url: Base WebSocket URL for the agent server (e.g., "ws://localhost:8000" or "ws://localhost:8000/ws")
                     The session_id will be appended automatically
    - parallel_executions: Number of parallel agents to run (each will focus on a different topic)
    - duration_minutes: Duration of the test in minutes
    - adversarial_model: (Optional) Model for generating adversarial queries
    - judge_model: (Optional) Model for analyzing responses
    
    Returns:
    - group_id: Unique identifier for this test group (used in report filename with "grp-" prefix)
    - session_ids: List of session IDs for all agents (can be used to check chat history via WebSocket)
    - status: "started" if successful
    - message: Status message
    
    Example request:
    {
        "websocket_url": "ws://localhost:8000",
        "parallel_executions": 3,
        "duration_minutes": 5
    }
    
    The consolidated report will be saved as: grp-{group_id}_{timestamp}.md and .json
    """
    import uuid
    from datetime import datetime
    
    # Validate inputs
    if request.parallel_executions < 1:
        return ParallelAdversarialResponse(
            group_id="",
            session_ids=[],
            status="error",
            message="parallel_executions must be at least 1"
        )
    
    if request.duration_minutes <= 0:
        return ParallelAdversarialResponse(
            group_id="",
            session_ids=[],
            status="error",
            message="duration_minutes must be greater than 0"
        )
    
    # Generate group ID
    group_id = f"grp-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    # Generate session IDs
    session_ids = [f"{group_id}-agent-{i+1}" for i in range(request.parallel_executions)]
    
    # Create group document in MongoDB
    group_doc = {
        "_id": group_id,
        "group_id": group_id,
        "session_ids": session_ids,
        "websocket_url": request.websocket_url,
        "parallel_executions": request.parallel_executions,
        "duration_minutes": request.duration_minutes,
        "adversarial_model": request.adversarial_model,
        "judge_model": request.judge_model,
        "status": "running",
        "created_at": datetime.utcnow(),
        "report_urls": {
            "markdown": None,
            "json": None
        }
    }
    
    try:
        groups_collection.insert_one(group_doc)
        print(f"Created group document: {group_id}")
    except Exception as e:
        print(f"Warning: Failed to create group document: {e}")
    
    # Start background task
    # The websocket_url should be the base URL (without session_id)
    # e.g., "ws://localhost:8000" or "ws://localhost:8000/ws"
    task = asyncio.create_task(
        run_parallel_adversarial_background(
            websocket_url=request.websocket_url,
            parallel_executions=request.parallel_executions,
            duration_minutes=request.duration_minutes,
            group_id=group_id,
            adversarial_model=request.adversarial_model,
            judge_model=request.judge_model
        )
    )
    running_tasks[group_id] = task
    
    return ParallelAdversarialResponse(
        group_id=group_id,
        session_ids=session_ids,
        status="started",
        message=f"Started {request.parallel_executions} parallel adversarial agents. They will run for {request.duration_minutes} minutes."
    )


@app.get("/api/adversarial/status/{group_id}")
async def get_adversarial_status(group_id: str):
    """Check if adversarial testing is still running"""
    is_running = group_id in running_tasks and not running_tasks[group_id].done()
    
    return {
        "group_id": group_id,
        "status": "running" if is_running else "completed",
        "is_running": is_running
    }


@app.get("/api/groups")
async def get_all_groups():
    """
    Get all group IDs.
    
    Returns:
    - A JSON array of group IDs
    """
    try:
        groups = list(groups_collection.find({}, {"group_id": 1, "_id": 0}))
        group_ids = [group["group_id"] for group in groups]
        return group_ids
    except Exception as e:
        return {
            "error": str(e),
            "groups": []
        }


@app.get("/api/groups/{group_id}")
async def get_group_metadata(group_id: str):
    """
    Get full metadata for a specific group.
    
    Parameters:
    - group_id: The group ID to retrieve metadata for
    
    Returns:
    - Full metadata object including:
      - group_id
      - session_ids
      - websocket_url
      - parallel_executions
      - duration_minutes
      - adversarial_model
      - judge_model
      - status (running, completed, failed)
      - created_at
      - completed_at (if completed)
      - report_urls (markdown and json S3 URLs)
      - error (if failed)
    """
    try:
        group = groups_collection.find_one({"group_id": group_id})
        
        if not group:
            return {
                "error": f"Group {group_id} not found"
            }
        
        # Convert ObjectId and datetime to strings for JSON serialization
        result = {
            "group_id": group.get("group_id"),
            "session_ids": group.get("session_ids", []),
            "websocket_url": group.get("websocket_url"),
            "parallel_executions": group.get("parallel_executions"),
            "duration_minutes": group.get("duration_minutes"),
            "adversarial_model": group.get("adversarial_model"),
            "judge_model": group.get("judge_model"),
            "status": group.get("status", "unknown"),
            "created_at": group.get("created_at").isoformat() if group.get("created_at") else None,
            "completed_at": group.get("completed_at").isoformat() if group.get("completed_at") else None,
            "report_urls": group.get("report_urls", {
                "markdown": None,
                "json": None
            }),
            "error": group.get("error")
        }
        
        return result
    except Exception as e:
        return {
            "error": str(e)
        }


@app.get("/api/session/{session_id}/messages")
async def get_session_messages(session_id: str):
    """
    Get all messages for a specific session in descending order (newest first).
    
    Uses pymongo directly to query the MongoDB memory collection (no langchain).
    
    Parameters:
    - session_id: The session ID to retrieve messages for
    
    Returns:
    - session_id: The session ID
    - message_count: Total number of messages
    - messages: Array of messages sorted by timestamp descending (newest first)
      Each message contains:
      - timestamp: ISO format timestamp
      - type: "human" or "ai"
      - content: The message content (input for human, output for ai)
    
    Example response:
    {
        "session_id": "test-session-1",
        "message_count": 4,
        "messages": [
            {
                "timestamp": "2025-12-27T12:34:56.789000",
                "type": "ai",
                "content": "This is the AI response..."
            },
            {
                "timestamp": "2025-12-27T12:34:55.123000",
                "type": "human",
                "content": "What is the question?"
            }
        ]
    }
    """
    try:
        # Query MongoDB directly using pymongo (no langchain)
        # Sort by timestamp descending (newest first)
        cursor = memory_collection.find(
            {'session_id': session_id}
        ).sort('timestamp', -1)  # -1 for descending order (newest first)
        
        messages = []
        for doc in cursor:
            # Handle timestamp conversion
            timestamp = doc.get('timestamp')
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
            elif timestamp:
                timestamp_str = str(timestamp)
            else:
                timestamp_str = datetime.utcnow().isoformat()
            
            message = {
                'timestamp': timestamp_str,
                'type': doc.get('type', 'unknown')
            }
            
            # Get content based on message type
            # Human messages have 'input', AI messages have 'output'
            if doc.get('input'):
                message['content'] = doc['input']
                message['type'] = 'human'
            elif doc.get('output'):
                message['content'] = doc['output']
                message['type'] = 'ai'
            else:
                # Skip if no content
                continue
            
            messages.append(message)
        
        return {
            'session_id': session_id,
            'message_count': len(messages),
            'messages': messages
        }
    
    except Exception as e:
        return {
            'session_id': session_id,
            'error': str(e),
            'message_count': 0,
            'messages': []
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

