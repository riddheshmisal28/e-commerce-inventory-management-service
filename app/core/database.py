from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine(
    settings.DATABASE_URL,
    echo = False,
    pool_pre_ping = True
)

SessionLocal = sessionmaker(
    bind = engine,
    autoflush= False,
    autoCommit = False,
)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yeild db
    finally:
        db.close()
