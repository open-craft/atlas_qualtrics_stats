import uuid

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Text, String


Session = sessionmaker()
Base = declarative_base()


class API_key(Base):
    __tablename__ = 'API_KEYS'
    key = Column(String(50), primary_key=True)

    @classmethod
    def new(cls):
        return cls(key=str(uuid.uuid4()))


class Job(Base):
    __tablename__ = 'JOBS'
    id = Column(String(100), primary_key=True)
    API_key = Column(String(50), ForeignKey('API_KEYS.key'), primary_key=True)
    xml_spec = Column(Text)
    value = Column(Text)
    created = Column(DateTime)
    last_run = Column(DateTime)


def init_db(conn_string):
    engine = create_engine(conn_string)
    Session.configure(bind=engine)
    Base.metadata.create_all(engine)


def gen_API_key():
    session = Session()
    api_key = API_key.new()
    session.add(api_key)
    session.commit()
    return api_key.key
