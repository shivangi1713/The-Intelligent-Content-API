import json
import logging
from typing import List, Tuple


from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .config import OPENAI_API_KEY
from .data_models.content_model import ContentCreate, ContentOut
from .data_models.user_model import Token, UserCreate, UserOut
from .db import models as db_models
from .db.database import Base, engine, get_db
from .utils.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

#DB setup
Base.metadata.create_all(bind=engine)

#LLM client (OpenAI) 
try:
    from openai import AsyncOpenAI

    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except Exception:  # pragma: no cover
    openai_client = None
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)    

#FastAPI app
app = FastAPI(
    title="The Intelligent Content API",
    description="Simple backend with signup/login and content analysis endpoints (Summary & Sentiment Analysis).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#Helper: analyze text with LLM (or fallback)
async def analyze_text_with_llm(text: str) -> Tuple[str, str]:
    """
    Returns (summary, sentiment).

    If OPENAI_API_KEY is not set or client is unavailable, or if the
    AI call fails, falls back to a simple heuristic so the API remains usable.
    """

    def simple_fallback(t: str) -> Tuple[str, str]:
        lowered = t.lower()
        sentiment = "Neutral"
        if any(w in lowered for w in ["good", "great", "excellent", "love", "happy"]):
            sentiment = "Positive"
        elif any(w in lowered for w in ["bad", "terrible", "awful", "hate", "sad"]):
            sentiment = "Negative"
        summary = t if len(t) <= 200 else t[:200] + "..."
        return summary, sentiment

    # No key / client not available → use fallback directly
    if not OPENAI_API_KEY or openai_client is None:
        logger.info("OPENAI_API_KEY not set or client unavailable; using fallback analysis.")
        return simple_fallback(text)

    try:
        completion = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize text and return JSON with keys "
                        '"summary" and "sentiment". '
                        'Sentiment must be exactly one of "Positive", "Negative", or "Neutral".'
                    ),
                },
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content
        data = json.loads(content)
        return data["summary"], data["sentiment"]

    except Exception as exc:
        # If OpenAI fails for any reason, do NOT crash the API
        logger.error("LLM call failed, falling back to simple heuristic: %s", exc)
        return simple_fallback(text)



#Health check
@app.get("/")
async def health_check():
    return {"status": "OK"}


#Auth endpoints
@app.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(
    user_in: UserCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(db_models.User).filter(db_models.User.email == user_in.email).first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed_password = get_password_hash(user_in.password)
    user = db_models.User(email=user_in.email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Treat "username" field from form as email
    user = (
        db.query(db_models.User)
        .filter(db_models.User.email == form_data.username)
        .first()
    )

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    access_token = create_access_token(subject=user.email)
    return Token(access_token=access_token)


#Content endpoints
@app.post("/contents", response_model=ContentOut, status_code=status.HTTP_201_CREATED)
async def create_content(
    payload: ContentCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    # 1) Store original text
    content = db_models.Content(text=payload.text, owner=current_user)
    db.add(content)
    db.commit()
    db.refresh(content)

    # 2) Analyze with LLM (or fallback)
    summary, sentiment = await analyze_text_with_llm(payload.text)
    content.summary = summary
    content.sentiment = sentiment
    db.commit()
    db.refresh(content)

    return content


@app.get("/contents", response_model=List[ContentOut])
async def list_contents(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    contents = (
        db.query(db_models.Content)
        .filter(db_models.Content.user_id == current_user.id)
        .order_by(db_models.Content.created_at.desc())
        .all()
    )
    return contents


@app.get("/contents/{content_id}", response_model=ContentOut)
async def get_content(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    content = (
        db.query(db_models.Content)
        .filter(
            db_models.Content.id == content_id,
            db_models.Content.user_id == current_user.id,
        )
        .first()
    )
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")
    return content


@app.delete("/contents/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user),
):
    content = (
        db.query(db_models.Content)
        .filter(
            db_models.Content.id == content_id,
            db_models.Content.user_id == current_user.id,
        )
        .first()
    )
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")

    db.delete(content)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)