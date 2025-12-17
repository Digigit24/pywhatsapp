from dotenv import load_dotenv
load_dotenv()
from app.db.session import get_db_session
from app.models.campaign import Campaign
import json

with get_db_session() as db:
    # Get latest campaign
    campaign = db.query(Campaign).order_by(Campaign.created_at.desc()).first()

    if campaign:
        print(f'Latest Campaign: {campaign.campaign_name}')
        print(f'ID: {campaign.campaign_id}')
        print(f'Total recipients: {campaign.total_recipients}')
        print(f'Sent: {campaign.sent_count}')
        print(f'Failed: {campaign.failed_count}')
        print(f'\nResults:')
        if campaign.results:
            for result in campaign.results:
                print(f'  {result}')
        else:
            print('  No results recorded')
    else:
        print('No campaigns found')
