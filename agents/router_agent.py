import os
import sys
import logging
from pathlib import Path

# Load environment variables for Gemini API Keys
from dotenv import load_dotenv
load_dotenv()

# Setup paths using pathlib
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END

# Import schemas and tools
from models.schema import RouterSchema, DataAgentSchema
from utils.llm_pick import pick_llm

# Import sub-agents
from agents.etl_agent import etl_analyst 
from agents.sql_analyst import sql_analyst

# ============================================================================
# Logging Configuration
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Data_Router_Agent")

# ============================================================================
# Router LLM Setup
# ============================================================================
llm = pick_llm("high")
llm_router = llm.with_structured_output(RouterSchema)

# ============================================================================
# Graph Nodes
# ============================================================================

def router_node(state: DataAgentSchema):
    """Analyzes user intent and routes to the appropriate specialized agent."""
    logger.info("Routing user request...")
    
    # Access Pydantic attributes via dot notation
    if not state.messages:
        raise ValueError("No messages found in state.")
        
    user_message = state.messages[-1].content
    
    try:
        route_response_dict = llm_router.invoke(user_message).model_dump()
        route_response = route_response_dict.get("answer", "").lower()
        
        logger.info(f"Router Decision: {route_response}")
        return {"route_response": route_response}
    except Exception as e:
        logger.error(f"Router failed to classify intent: {e}")
        return {"route_response": "error"}


def etl_node(state: DataAgentSchema):
    """Delegates execution to the ETL Analyst Sub-Graph."""
    logger.info("Delegating task to ETL Agent...")
    
    user_message = state.messages[-1].content
    
    response = etl_analyst.invoke({
        "messages": [HumanMessage(content=user_message)]
    }) 
    
    # Safely extract the final message from the sub-graph's state
    final_message = response.get("messages", [])[-1] if response.get("messages") else AIMessage(content="ETL process completed without returning a message.")
    
    return {"messages": [final_message]}


def sql_node(state: DataAgentSchema):
    """Delegates execution to the SQL Analyst Sub-Graph."""
    logger.info("Delegating task to SQL Agent...")
    
    user_message = state.messages[-1].content
    
    input_schema = {
        "messages": [],
        "user_question": user_message,
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }
    
    response = sql_analyst.invoke(input_schema)
    
    # Extract the final_answer text to maintain a clean message history in the parent graph
    final_answer = response.get("final_answer", "SQL analysis completed.")
    
    return {"messages": [AIMessage(content=final_answer)]}


# ============================================================================
# Graph Routing Logic
# ============================================================================

def route_edge(state: DataAgentSchema) -> str:
    """Conditional edge to direct traffic based on the router's decision."""
    # Use getattr for safe access on Pydantic objects just in case it is unset
    route = getattr(state, "route_response", "")
    
    if route == "sql":
        return "sql_node"
    elif route == "etl":
        return "etl_node"
    else:
        logger.warning(f"Invalid or missing route response: '{route}'. Halting execution.")
        return END


# ============================================================================
# Graph Compilation
# ============================================================================

data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")

# Conditional routing from router -> specialized agents
data_agent_graph.add_conditional_edges(
    "router_node", 
    route_edge,
    {
        "sql_node": "sql_node",
        "etl_node": "etl_node",
        END: END
    }
)

# Explicitly end the graph after the specialized agents finish
data_agent_graph.add_edge("etl_node", END)
data_agent_graph.add_edge("sql_node", END)

data_agent = data_agent_graph.compile()


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    
    # Save Graph Visualization
    try:
        from IPython.display import Image
        img_data = data_agent.get_graph().draw_mermaid_png()
        with open("router_agent_graph.png", "wb") as f:
            f.write(img_data)
        logger.info("Graph visualization saved to 'data_agent_graph.png'")
    except Exception as e:
        logger.warning(f"Could not generate graph visualization: {e}")

    # Invoke the Router Agent
    initial_state = {
        "messages": [
            HumanMessage(
                content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv folder"
            )
        ],
        "route_response": ""
    }
    
    logger.info("Starting Data Router Agent...")
    response = data_agent.invoke(initial_state)

    print("\n" + "=" * 80)
    print("FINAL PARENT GRAPH RESPONSE")
    print("=" * 80)
    
    # Safely print the final message
    final_messages = getattr(response, "messages", []) if not isinstance(response, dict) else response.get("messages", [])
    if final_messages:
        print(final_messages[-1].content)
    else:
        print("No final message generated.")