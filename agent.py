from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, room_io, ChatContext, ChatMessage
from livekit.plugins import (
    ai_coustics,
)
from livekit.plugins import google
from mem0 import AsyncMemoryClient
import json
import logging
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from tools.tools import get_weather, search_web

load_dotenv(".env")


class Assistant(Agent):
    def __init__(self, chat_ctx=None) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice="Fenrir",
                temperature=0.8,
            ),
            tools=[get_weather, search_web],
            chat_ctx=chat_ctx,
        )


server = AgentServer()


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: agents.JobContext):

    async def shutdown_hook(
        chat_ctx: ChatContext, mem0: AsyncMemoryClient, memory_str: str
    ):
        logging.info("Shutting down hook, saving chat context to memory...")

        messages_formatted = []
        logging.info(f"Chat context messages: {chat_ctx.items}")

        for item in chat_ctx.items:
            if not isinstance(item, ChatMessage):
                continue
            if isinstance(item.content, list):
                content_str = "".join(
                    part for part in item.content if isinstance(part, str)
                )
            else:
                content_str = str(item.content) if item.content else ""

            if memory_str and memory_str in content_str:
                continue

            if item.role in ["user", "assistant"]:
                messages_formatted.append(
                    {
                        "role": item.role,
                        "content": content_str.strip(),
                    }
                )
        logging.info(f"Formatted messages to add to memory: {messages_formatted}")
        await mem0.add(messages_formatted, user_id="Jens")
        logging.info("Chat context saved to memory")

    session = AgentSession()

    mem0 = AsyncMemoryClient()
    user_name = "Jens"

    results = await mem0.get_all(filters={"user_id": user_name})
    initial_ctx = ChatContext()
    memory_str = ""

    if results:
        memories = [
            {
                "memory": result["memory"],
                "updated_at": result["updated_at"],
            }
            for result in results["results"]
        ]
        memory_str = json.dumps(memories)
        logging.info(f"Memories: {memory_str}")
        initial_ctx.add_message(
            role="assistant",
            content=f"The user's name is {user_name}, and this is the relevant context about him: {memory_str}",
        )

    await session.start(
        room=ctx.room,
        agent=Assistant(chat_ctx=initial_ctx),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S
                ),
            ),
        ),
    )

    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )

    ctx.add_shutdown_callback(
        lambda: shutdown_hook(session._agent.chat_ctx, mem0, memory_str)
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
