from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.github import router as github_router
from app.routers.jira import router as jira_router
from app.routers.documents import router as documents_router
from app.routers.search import router as search_router
from app.routers.rag import router as rag_router
from app.routers.assistant import router as assistant_router
from app.routers.conversations import router as conversations_router
from app.routers.chat import router as chat_router

app = FastAPI(
    title="Enterprise AI Project Management Assistant",
    version="1.0.0"
)

# Allowed origins for frontend clients
# Allowed origins for frontend clients (including local dev and production URL)
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
# Remove any None entries
origins = [origin for origin in origins if origin]

# Enable CORS for frontend clients with credential support
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(github_router)
app.include_router(jira_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(rag_router)
app.include_router(assistant_router)
app.include_router(conversations_router)
app.include_router(chat_router)


@app.get("/")
def home():
    return {
        "message": "Enterprise AI Project Management Assistant API"
    }
