"""SQLAlchemy ORM for paper storage and deduplication."""

import os

from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(String, unique=True, nullable=False)
    doi = Column(String, unique=True, index=True)
    title = Column(Text)
    abstract = Column(Text)
    authors = Column(Text)  # JSON string
    year = Column(Integer)
    venue = Column(String)
    journal = Column(String)
    url = Column(String)
    publication_types = Column(String)
    publication_date = Column(String)
    fields_of_study = Column(String)
    citation_count = Column(Integer)
    is_open_access = Column(Integer)
    open_access_pdf = Column(String)


def get_session(db_path: str = "output") -> Session:
    """Create database session. DB file lives at {db_path}/papers.db."""
    os.makedirs(db_path, exist_ok=True)
    db_file = os.path.join(db_path, "papers.db")
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()
