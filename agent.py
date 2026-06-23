import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from tools import TOOLS, call_tool

load_dotenv()

llm_client = OpenAI(
    api_key=os.environ['OPENROUTER_API_KEY'],
    base_url=os.environ['BASE_URL'],
)

SYSTEM_PROMPT = '''You are a helpful assistant that answers questions about documents.

You have two tools:
- search_documents: search the document knowledge base
- get_session_history: retrieve conversation history

Always search documents before answering. Use history when the user references previous messages.
If the answer is not in the documents, say so honestly.'''

def run_agent(question: str, session_id: str) -> str:
    '''Run agent and returned final answer'''
    messages = [
        {'role':'system', 'content': SYSTEM_PROMPT},
        {'role':'user', 'content': question},
    ]

    while True:
        response = llm_client.chat.completions.create(
            model=os.environ['BASE_MODEL'],
            messages=messages,
            tools=TOOLS,
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content or ''
        
        messages.append(msg)
        for tc in msg.tool_calls:
            result = call_tool(tc.function.name, tc.function.arguments, session_id)
            messages.append({
                'role':'tool',
                'tool_call_id': tc.id,
                'content': result,
            })

if __name__ == '__main__':
    # fast check without FastAPI
    answer = run_agent('What is RAG', session_id='test')
    print(answer)