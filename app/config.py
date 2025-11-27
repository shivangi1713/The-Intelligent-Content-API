import os
from dotenv import load_dotenv

load_dotenv()

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

DATABASE_URL = os.getenv("DATABASE_URL")  

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  