from sqlalchemy import create_engine, make_url
from sqlalchemy.orm import sessionmaker

from app.settings import load_settings


DATABASE_URL = load_settings().database_url

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada en el archivo .env")

raw_url = (
    "postgresql://" + DATABASE_URL[len("postgres://") :]
    if DATABASE_URL.startswith("postgres://")
    else DATABASE_URL
)
url = make_url(raw_url)
if url.drivername == "postgresql":
    url = url.set(drivername="postgresql+pg8000")

engine = create_engine(url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)