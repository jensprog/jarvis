import os
import logging
from livekit.agents import function_tool, RunContext
import requests
from langchain_community.tools import DuckDuckGoSearchRun
from dotenv import load_dotenv

load_dotenv(".env")

""" Fetching the weather from different cities """


@function_tool()
async def get_weather(context: RunContext, city: str) -> str:
    try:
        response = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={os.getenv('OPEN_WEATHER_API_KEY')}"
        )
        if response.status_code == 200:
            logging.info(f"Weather for {city}: {response.text.strip()}")
            return response.text.strip()
        else:
            logging.error(f"Weather for {city}: {response.status_code}")
            return f"Could not retrieve weather for {city}."
    except Exception as e:
        logging.error(f"Error while trying to retrieve weather for {city}: {e}")
        return f"Could not retrieve weather for {city}."


""" Search the web using DuckDuckGo"""


@function_tool()
async def search_web(context: RunContext, query: str) -> str:
    try:
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logging.info(f"Search results for {query}: {results}")
        return results
    except Exception as e:
        logging.error(f"Error while trying to search the web for {query}: {e}")
        return f"Could not search the web for {query}."
