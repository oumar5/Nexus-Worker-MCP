import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import httpx

load_dotenv()

async def main():
    api_key = os.getenv("WORKER_API_KEY")
    api_base = os.getenv("WORKER_API_BASE_URL")
    api_version = os.getenv("WORKER_API_VERSION")

    async def log_request(request: httpx.Request):
        print(f"Request URL: {request.url}")

    http_client = httpx.AsyncClient(event_hooks={'request': [log_request]})

    default_headers = {"Ocp-Apim-Subscription-Key": api_key}
    
    # Construction du base_url dynamique
    model = "gpt-4o"
    base_url = f"{api_base.rstrip('/')}/deployments/{model}"
    
    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key, # Peut être ignoré avec APIM mais obligatoire pour instancier
        default_headers=default_headers,
        default_query={"api-version": api_version},
        http_client=http_client,
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        print("Success:", response.choices[0].message.content)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
