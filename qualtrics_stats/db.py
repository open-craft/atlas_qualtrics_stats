import uuid

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

    @classmethod
    def new(cls):
        return cls(key=str(uuid.uuid4()))


class Job(Base):
    __tablename__ = 'JOBS'
    id = Column(String, primary_key=True)
    API_key = Column(String, ForeignKey('API_KEYS.key'), primary_key=True)
    xml_spec = Column(String)
    value = Column(String)
    created = Column(DateTime)
    last_run = Column(DateTime)


Base.metadata.create_all(engine)


def gen_API_key():
    session = Session()
    api_key = API_key.new()
    session.add(api_key)
    session.commit()
    return api_key.key
