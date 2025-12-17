from dotenv import load_dotenv
load_dotenv()
from app.db.session import get_db_session
from app.models.message import Message

with get_db_session() as db:
    phones = ['+918793944961', '+919142982138']
    for phone in phones:
        incoming = db.query(Message).filter(
            Message.phone == phone,
            Message.direction == 'incoming'
        ).count()

        outgoing = db.query(Message).filter(
            Message.phone == phone,
            Message.direction == 'outgoing'
        ).count()

        print(f'{phone}:')
        print(f'  Incoming: {incoming}, Outgoing: {outgoing}')
        print(f'  Status: {"OPTED_IN" if incoming > 0 else "NOT_OPTED_IN"}')
