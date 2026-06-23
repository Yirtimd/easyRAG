import os
import secrets
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Session
from dotenv import load_dotenv


load_dotenv()

class Base(DeclarativeBase):
    pass

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f'Message session={self.session_id} role={self.role}'
    
class User(Base):
    __tablename__ = 'Users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key = Column(String(64), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


    
engine = create_engine(os.environ['DATABASE_URL'], echo=False)
Base.metadata.create_all(engine)

def get_history(session_id: str, limit: int = 10) -> list[dict]:
    with Session(engine) as db:
        message = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {'role': m.role, 'content': m.content}
            for m in reversed(message)
        ]
    
def save_message(session_id: str, role: str, content: str) -> None:
    with Session(engine) as db:
        db.add(Message(session_id=session_id, role=role, content=content))
        db.commit()

def create_user() -> dict:
    '''Create new user and returned api key'''
    key = 'sk-' + secrets.token_hex(24)
    with Session(engine) as session:
        user = User(api_key=key)
        session.add(user)
        session.commit()
        session.refresh(user)
        return {'id': user.id, 'api_key': user.api_key}
    
def get_user_by_key(api_key: str) -> dict | None:
    '''Finds user by API
       Returns None if no matching user is found
    ''' 
    with Session(engine) as session:
        user = session.query(User).filter(User.api_key == api_key).first()
        if not user:
            return None
        return {'id':user.id, 'api_key': user.api_key}




if __name__ == "__main__":
    # Быстрая проверка
    save_message("test-session", "user", "What is RAG?")
    save_message("test-session", "assistant", "RAG stands for...")
    history = get_history("test-session")
    print(f"История: {len(history)} сообщений")
    for msg in history:
        print(f"  {msg['role']}: {msg['content'][:50]}")

