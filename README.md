# The Intelligent Content API (Backend)
A FastAPI-based backend that lets authenticated users submit text content and automatically receive a summary and sentiment (Positive, Negative, Neutral).
The system stores users and their contents in a relational database and integrates an LLM (OpenAI) for analysis.

This project is a small FastAPI backend that lets users:

1. **Sign up** with an email + password  
2. **Log in** and receive a **JWT access token**  
3. **Submit text content** (e.g. meeting notes, conversation summaries)  
4. Automatically compute:
   - a short **summary**
   - a simple **sentiment**: `Positive`, `Negative`, or `Neutral`  
5. **List**, **fetch**, and **delete** their own contents
It implements the full assignment: authentication, AI integration, database persistence, Docker, CI, and a GCP deployment plan.
---
## 1. Setup Instructions

### 1.1 Environment Variables
Create a .env file in the project root:

```bash
   # Database
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/ai_analyzer

# Auth
JWT_SECRET_KEY=_KX6uBnw1H2y1sG3AjU4v9A3pGZgqLtaF3k8jZqs
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

# OpenAI
OPENAI_API_KEY=
   ```
---
### 1.2 Running the Project Locally

Setup to run dockerfile

   ```bash
   docker build -t int-content-api .
   docker start content
   docker network create ai-nets
   docker network connect ai-nets content
   docker run --name int-content-api --network ai-nets --env-file .env.docker -p 8000:8000 int-content-api
   ```

After setup you can start or stop app with single line command. 

   ```bash
   docker start int-content-api
   docker stop int-content-api
   ```

### 1.3 Create and Activate Virtual Environment

```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

### 1.4 Install Dependencies

```bash
   python.exe -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

### 1.5 Run the App

```bash
uvicorn app.main:app --reload
```  

The app will be available at:


1. **Open Swagger UI**: `http://localhost:8000/docs`

2. **Sign up**:  
   Call `POST /signup` with a new email + password.

3. **Login**:  
   Click the **Authorize** button, enter email/password.

4. **Create content**:  
   Use `POST /contents` with a paragraph of text.

   ## Sample input to try the app
{
  "text": "Today we discussed the upcoming project deadlines for the AI Summary Sentiment Analyzer. The team agreed that the current timeline is tight but still achievable if we prioritize the core features and reduce some nice-to-have items. We decided that the backend APIs for signup, login, and content storage must be finalized by next week. After that, we will focus on polishing the summary and sentiment analysis logic and writing clear documentation. Everyone also mentioned that testing coverage is still weak, so we will schedule an additional review session to identify missing test cases and fix critical bugs before the final demo."
}

5. **List content**:  
   Use `GET /contents`.

6. **Optionally get/delete by ID**:  
   `GET /contents/{id}` and `DELETE /contents/{id}`.

This covers authentication, authorization, database persistence, and AI-powered text analysis

## 2. API Documentation

The API is documented using auto-generated Swagger UI at: `http://localhost:8000/docs`.

### 2.1 Health check

**Endpoint:** `GET /`  
**Description:** Quick check that the app is running.

Expected response:

```json
{ "status": "OK" }
```


### 2.2 Sign up

**Endpoint:** `POST /signup`  
**Description:** Register a new user.

Example body:

```json
{
  "email": "test@example.com",
  "password": "mypassword123"
}
```

Expected response (201):

```json
{
  "id": 1,
  "email": "test@example.com"
}
```

If the email already exists, you should get:

```json
{
  "detail": "Email already registered."
}
```


### 2.3 Login via Swagger **Authorize**

The app uses OAuth2 password flow with JWTs.

1. Go to `http://localhost:8000/docs`.
2. Click the green **Authorize** button at the top-right.
3. In the popup:
   - `username` = your email (e.g. test@example.com)
   - `password` = your password
   - Leave `client_id` and `client_secret` empty.
4. Click **Authorize**, then **Close**.

Swagger will:

- Call `POST /login` behind the scenes.
- Store the returned `access_token`.
- Automatically attach `Authorization: Bearer <token>` to all protected requests (`/contents` endpoints).

You can also manually call `POST /login` if you want to see the raw JSON:

```json
{
  "access_token": "<JWT_TOKEN>",
  "token_type": "bearer"
}
```


### 2.4 Create content (summary + sentiment)

**Endpoint:** `POST /contents`  
**Auth:** Required (must be logged in).

Example request body:

```json
{
  "text": "Today we discussed the upcoming project deadlines for the AI Summary Sentiment Analyzer. The team agreed that the current timeline is tight but achievable if we prioritize core features and improve our testing process."
}
```

Example response:

```json
{
  "id": 1,
  "text": "Today we discussed the upcoming project deadlines for the AI Summary Sentiment Analyzer. ...",
  "summary": "Short summary of the discussion ...",
  "sentiment": "Positive"
}
```

### 2.5 List contents

**Endpoint:** `GET /contents`  
**Auth:** Required.

Returns all contents belonging to the logged-in user:

```json
[
  {
    "id": 1,
    "text": "...",
    "summary": "...",
    "sentiment": "Positive"
  },
  {
    "id": 2,
    "text": "...",
    "summary": "...",
    "sentiment": "Neutral"
  }
]
```

---

### 2.6 Get content by ID

**Endpoint:** `GET /contents/{content_id}`  
**Auth:** Required.

If the item exists and belongs to the current user, it returns a single content object.  
If not, returns `404 Content not found`.

---

### 2.7 Delete content

**Endpoint:** `DELETE /contents/{content_id}`  
**Auth:** Required.

On success, returns `204 No Content`.  
Subsequent calls to `GET /contents/{content_id}` for that ID will return `404`.

---

## 3. Design Decisions

### 3.1 Database Choice

- Used **PostgreSQL** as a relational DB:
  - Easy to run locally via Docker.
  - Natural fit for user authentication and content with clear relationships.

### 3.2 AI Integration

- Chosen model: `gpt-4o-mini` (via the OpenAI Chat Completions API).
  - Good balance of quality, speed, and cost.
- Prompts the model to return structured JSON with `summary` and `sentiment`, which simplifies parsing.
- If `OPENAI_API_KEY` is not set or the API call fails:
  - A lightweight heuristic provides:
    - Sentiment based on positive/negative keywords.
    - Summary as a truncated version of the input text.

This ensures the API still works even without external network access or API keys.

### 3.3 Async Processing

- LLM calls use the async OpenAI client inside `async def` endpoints, e.g. `await openai_client.chat.completions.create(...)`.
- This keeps the event loop responsive rather than blocking per request.

### 3.4 Security & Secrets

- No API keys or database URLs are hard-coded.
- All secrets come from `.env`.
- JWT secret is randomly generated by the developer and stored only in `.env`.
- Passwords are never stored in plain text; they’re hashed via `passlib`.

---

## 4. CI/CD with GitHub Actions (Basic)

A minimal GitHub Actions workflow can be placed in:

```text
.github/workflows/ci.yml
```

This ensures that on each push to `main`:

- The code at least installs successfully.
- A basic test suite runs (once you add `pytest` tests).
---
## 13. Deployment Architecture on GCP (Theoretical)
![GCP Deployment Architecture - Intelligent Content API](https://github.com/user-attachments/assets/7a3da7d8-c940-4ea8-9e05-b1a635f9f739)

The client sends HTTPS requests to API Gateway, which routes traffic to the containerized FastAPI service running on Cloud Run. The service persists data in Cloud SQL (PostgreSQL), reads secrets and configuration from Secret Manager, and calls the external OpenAI API for summarization and sentiment analysis. Logs and metrics are centralized via Cloud Logging / Monitoring.

This architecture is fully managed, scales automatically, and keeps secrets out of the codebase.


---
