from backend.ai_agent import AIAgent
import asyncio
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def test_date_extraction():
    agent = AIAgent()
    
    # Test cases
    test_messages = [
        'Let\'s go in September',
        'How about next summer?',
        'I think October would be perfect',
        'Maybe this December?',
        'I prefer budget accommodations'
    ]
    
    for msg in test_messages:
        print(f'Testing: \"{msg}\"')
        intent = await agent._detect_intent(msg)
        print(f'  Intent: {intent.intent}')
        print(f'  Month: {intent.extracted_month}')
        print(f'  Year: {intent.extracted_year}')
        print(f'  Date mentions: {intent.date_mentions}')
        print()

asyncio.run(test_date_extraction())