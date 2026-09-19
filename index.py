import asyncio
import uuid
from tool import get_tools, add_infomation, get_infomation, update_infomation, Context
from memory import setup_postgres_store
from deepagents import create_deep_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from prompt import system_prompt
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()  # Load biến môi trường từ .env

async def main():
    mcp_tools = await get_tools()
    memory_tools = [add_infomation, get_infomation, update_infomation]
    tools = mcp_tools + memory_tools

    model = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.9)

    checkpointer = InMemorySaver()
    thread_id = str(uuid.uuid4())  # 1 thread = 1 phiên hội thoại

    with setup_postgres_store() as store:
        store.setup()
        agent = create_deep_agent(
            model=model,
            tools=tools,
            store=store,
            checkpointer=checkpointer,
            context_schema=Context,
            system_prompt=system_prompt,
        )

        config = {"configurable": {"thread_id": thread_id}}

        query = input("Nhập câu hỏi của bạn: ")
        while query.lower() != "exit":
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": query}]},
                context=Context(user_id="user_123"),
                config=config,
            )
            print(result["messages"][-1].content[0]['text'])
            query = input("Nhập câu hỏi của bạn: ")


if __name__ == "__main__":
    asyncio.run(main()) 