from app.services.provider_service import ProviderService
from app.agents import state
from langchain.agents import create_agent
from app.core.logging import get_logger
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


logger = get_logger(__name__)

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentChatState(TypedDict):
    """
    Shared state for the CV analysis LangGraph pipeline.
    Each node reads from it, performs work, and returns updates to merge back.
    """
    language:str
    provider:str
    model:str
    api_key:str
    recommendations:str
    score:str
    job_description:str
    cv:str
    messages:Annotated[list, add_messages]
    user_message:str

def _build_system_prompt(state: AgentChatState) -> str:
  """
  Builds the prompt for the recommendation node.
  """

  language = state["language"]
  lang = "French" if language == "fr" else "English"
  return  f"""
  tu est un assistant IA specialiste en CV et en recrutement
  vous devez fournir des reponses en {lang} uniquement
  et dans un ton profesional , amicale et chaleureux

  voici l'historique des messages :
  - {state['messages']}
  
  voici les informations que tu dois prendre en consideration :
  - recommendations : {state['recommendations']}
  - score : {state['score']}
  - job_description : {state['job_description']}
  - cv : {state['cv']}
  - les notes sont de 0 a 100 , 0 = no match, 50 = partial match, 80+ = strong match, 100 = perfect match
  A partir des elements suivants tu dois construire un message pour l'utilisateur
  l'utilisateur pose des questions et tu dois repondre en se basant sur les elements suivants
  tu dois utiliser les messages precedents pour construire un message pertinent et coherant
  toujours a la suite de la conversation que tu viens de commencer avec l'utilisateur

  """


async def resume_recommendation_node(state: AgentChatState) -> dict:
  """
  Répond à la question de l'utilisateur en se basant sur le CV, l'offre,
  le score et les recommandations déjà calculés.
  """
  llm = ProviderService.get_llm(
            provider=state["provider"],
            model=state["model"],
            api_key=state["api_key"],
        )

  user_message = HumanMessage(
      content=f"question de l'utilisateur : \n {state['user_message']} \n reponds lui maintenant"
  )

  messages = [
      SystemMessage(content=_build_system_prompt(state)),
      user_message,
  ]

  response = await llm.ainvoke(messages)

  # add_messages fusionne ces messages avec l'historique existant
  return {"messages": [user_message, response]}

    


def build_agent_chat_graph() -> CompiledStateGraph:

  graph = StateGraph(AgentChatState)

  graph.add_node("agent", resume_recommendation_node)
  graph.add_edge(START,"agent")
  graph.add_edge("agent",END)
  compiled = graph.compile()
  logger.info("LangGraph agent chat compiled successfully")
  return compiled

# Singleton graph instance
agent_chat_graph = build_agent_chat_graph()

