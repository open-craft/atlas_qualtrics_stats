from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, String


# The db location is quite ugly, but it's supposed not to be definitive anyway
engine = create_engine('sqlite:///qualtrics_stats.db')

Session = sessionmaker(bind=engine)

Base = declarative_base()


class API_key(Base):
    __tablename__ = 'API_KEYS'
    key = Column(String, primary_key=True)


class Job(Base):
    __tablename__ = 'JOBS'
    id = Column(String, primary_key=True)
    API_key = Column(String, ForeignKey('API_KEYS.key'))
    xml_spec = Column(String)
    value = Column(String)
    created = Column(DateTime)
    last_run = Column(DateTime)


Base.metadata.create_all(engine)
