import sys
import logging
import traceback
import io
from pathlib import Path
from contextlib import redirect_stdout
from typing import Annotated, TypedDict, Optional, List, Dict, Any
from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# Environment and Path Setup
# ============================================================================
# Use pathlib instead of os.path (Requirement #4, #17)
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# Preserved project structure imports
from utils.llm_pick import pick_llm
from utils.etl_tools import ETLTools

# ============================================================================
# Logging Configuration (Requirement #3)
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ETL_Agent")

# ============================================================================
# State Schema (Requirement #21)
# ============================================================================
# Defining locally to ensure all newly required fields are strictly present.
# This acts as an upgraded version of the original ETLAgentSchema.
class ETLAgentSchema(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    current_file: Optional[str]
    output_folder: Optional[str]
    output_format: Optional[str]
    generated_code: Optional[str]
    execution_result: Optional[str]
    error: Optional[str]
    retry_count: int
    iterations: int

# ============================================================================
# Helper Functions (Requirement #2, #8, #14, #26)
# ============================================================================
def extract_python_code(text: str) -> str:
    """
    Safely extracts Python code from an LLM response, stripping Markdown formatting.
    """
    text = text.strip()
    if text.startswith("```"):
        # Split by newlines, drop the first line (```python) and last line (```)
        lines = text.split("\n")
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return text.strip()

def safe_execute_pandas(code: str) -> Dict[str, Any]:
    """
    Executes generated Pandas code in a restricted scope. (Requirement #14)
    Avoids unsafe global exec and returns structured results.
    """
    import pandas as pd
    
    # Restrict globals to basic builtins and pandas/pathlib
    restricted_globals = {
        "__builtins__": __builtins__,
        "pd": pd,
        "Path": Path
    }
    
    stdout_trap = io.StringIO()
    try:
        # Redirect stdout to capture print statements from the executed code
        with redirect_stdout(stdout_trap):
            exec(code, restricted_globals)
            
        output = stdout_trap.getvalue()
        return {"status": "success", "output": output, "error": None}
    
    except Exception as e:
        error_msg = f"{traceback.format_exc()}\nException: {str(e)}"
        return {"status": "error", "output": stdout_trap.getvalue(), "error": error_msg}

# ============================================================================
# Agent Tools (Requirement #12)
# ============================================================================

@tool
def extract_load_tool(url: str, output_folder: str, format: str) -> str:
    """
    Use this tool to extract raw data from an API (url) and save it to a local folder.
    
    Args:
        url (str): The API endpoint to fetch data from.
        output_folder (str): The local directory path where data will be saved.
        format (str): Target file format ('csv', 'json', or 'parquet').
        
    Returns:
        str: Success or failure message detailing the extraction result.
    """
    logger.info(f"Executing extract_load_tool for URL: {url}")
    try:
        # Auto-create folders if missing (Requirement #18)
        folder_path = Path(output_folder)
        folder_path.mkdir(parents=True, exist_ok=True)
        
        etl_tools = ETLTools()
        # Convert path to string for backwards compatibility with ETLTools
        result = etl_tools.extract_load(url, str(folder_path), format)
        return f"Successfully extracted and loaded data: {result}"
        
    except Exception as e:
        error_msg = f"Failed to extract and load data: {str(e)}"
        logger.error(error_msg)
        return error_msg


@tool
def transform_load_tool(input_file_path: str, output_folder: str, output_format: str, user_question: str) -> str:
    """
    Use this tool to read an existing data file, transform it using Pandas based on a user request,
    and save the transformed data to a new folder.
    
    Args:
        input_file_path (str): The absolute or relative path to the source data file.
        output_folder (str): The folder where the transformed file will be saved.
        output_format (str): The target format for the transformed data ('csv', 'json', or 'parquet').
        user_question (str): The natural language instruction describing the desired transformation.
        
    Returns:
        str: A message indicating the success or failure of the transformation, including generated code.
    """
    logger.info(f"Executing transform_load_tool on {input_file_path}")
    
    input_path = Path(input_file_path)
    out_dir = Path(output_folder)
    out_dir.mkdir(parents=True, exist_ok=True) # (Requirement #18)
    
    if not input_path.exists():
        return f"Error: Input file does not exist at {input_path.absolute()}"

    etl_tools = ETLTools()
    try:
        top_rows = etl_tools.transform_load_context(str(input_path))
    except Exception as e:
        return f"Error reading context from input file: {e}"

    # Use "medium" model for code generation (Requirement #9)
    llm = pick_llm("medium")

    # (Requirement #7, #15, #16)
    system_prompt = f"""You are an elite Python Data Analyst.
Task: Write Pandas code to transform data based on the user's question.

Input file: {input_path.absolute()}
Output folder: {out_dir.absolute()}
Target format: {output_format}
User Question: {user_question}
Data Context (top 3 rows):
{top_rows}

RULES:
1. Return ONLY valid, executable Python code. NO markdown formatting. NO explanations. NO comments.
2. MUST import pandas as pd.
3. MUST read the input file into a DataFrame.
4. MUST apply the requested transformations.
5. MUST save the resulting DataFrame to the output folder using the correct format extension.
6. Use pathlib to handle directory creations safely inside the code if necessary.
"""

    messages: List[BaseMessage] = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Generate the Pandas code now.")
    ]

    # Retry logic (Requirement #13)
    max_retries = 3
    last_error = ""

    for attempt in range(1, max_retries + 1):
        logger.info(f"Pandas code generation attempt {attempt}/{max_retries}")
        try:
            response = llm.invoke(messages)
            pandas_code = extract_python_code(response.content)
            
            logger.info("Executing generated Pandas code...")
            exec_result = safe_execute_pandas(pandas_code)
            
            if exec_result["status"] == "success":
                success_msg = (
                    f"Data successfully transformed and saved to {out_dir.absolute()}.\n\n"
                    f"--- Executed Code ---\n{pandas_code}\n\n"
                    f"--- Output ---\n{exec_result['output']}"
                )
                logger.info("Transformation successful.")
                return success_msg
            else:
                last_error = exec_result["error"]
                logger.warning(f"Code execution failed on attempt {attempt}: {last_error}")
                
                # Feedback loop for self-correction
                messages.append(AIMessage(content=pandas_code))
                messages.append(HumanMessage(
                    content=f"Execution failed with error:\n{last_error}\nFix the code and return ONLY the corrected Python code."
                ))
                
        except Exception as e:
            last_error = str(e)
            logger.error(f"Unexpected error during code generation/execution: {last_error}")
            messages.append(HumanMessage(content=f"An unexpected error occurred: {last_error}. Please correct the code."))

    return f"CRITICAL FAILURE: Failed to transform data after {max_retries} attempts. Last Error:\n{last_error}"


# Define toolkit
tools = [extract_load_tool, transform_load_tool]

# ============================================================================
# Graph Nodes & Routing (Requirement #1, #10, #11, #22)
# ============================================================================

def llm_node(state: ETLAgentSchema) -> Dict[str, Any]:
    """
    Main reasoning node. Evaluates user input, checks graph iteration bounds, 
    and determines which tool to call.
    """
    iterations = state.get("iterations", 0) + 1
    
    # Prevent infinite loops (Requirement #22)
    if iterations > 5:
        logger.warning("Maximum graph iterations reached. Halting to prevent infinite loop.")
        return {
            "iterations": iterations,
            "messages": [AIMessage(content="I have reached the maximum number of steps allowed. Please refine your request.")]
        }

    # Bind tools to the high-tier reasoning model (Requirement #9)
    llm = pick_llm("high").bind_tools(tools)
    
    # Proper system message parsing (Requirement #11)
    system_msg = SystemMessage(
        content="You are a Senior Data Engineer Agent managing an ETL pipeline. "
                "You have tools to extract data from APIs and to transform data using Pandas. "
                "Analyze the user's request, identify the appropriate tool, and pass the exact required arguments. "
                "Once the tool has successfully completed the task, provide a concise final summary to the user."
    )
    
    # Ensure SystemMessage is always present at the start
    current_messages = state.get("messages", [])
    if not current_messages or not isinstance(current_messages[0], SystemMessage):
        invoke_messages = [system_msg] + current_messages
    else:
        invoke_messages = current_messages

    logger.info(f"Agent Reasoning Iteration: {iterations}")
    response = llm.invoke(invoke_messages)
    
    return {"messages": [response], "iterations": iterations}


def route_tools(state: ETLAgentSchema) -> str:
    """
    Conditional edge router. Determines if a tool call was requested by the LLM.
    """
    messages = state.get("messages", [])
    if not messages:
        return END
        
    last_message = messages[-1]
    
    # If the LLM returned a tool call, route to the tool_node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"
        
    # Otherwise, execution is finished
    return END

# ============================================================================
# Graph Compilation (Requirement #1, #27)
# ============================================================================

etl_analyst_graph = StateGraph(ETLAgentSchema)

# Add Nodes
etl_analyst_graph.add_node("llm_node", llm_node)
# Utilizing LangGraph's prebuilt ToolNode instead of manual tool execution (Requirement #10)
etl_analyst_graph.add_node("tool_node", ToolNode(tools))

# Add Edges
etl_analyst_graph.add_edge(START, "llm_node")
etl_analyst_graph.add_conditional_edges("llm_node", route_tools, {"tool_node": "tool_node", END: END})
etl_analyst_graph.add_edge("tool_node", "llm_node")

# Compile
etl_analyst = etl_analyst_graph.compile()

# ============================================================================
# Execution (Main)
# ============================================================================
if __name__ == "__main__":
    
    # Improve graph visualization (Requirement #23)
    try:
        from IPython.display import Image
        img_data = etl_analyst.get_graph().draw_mermaid_png()
        with open("etl_analyst_graph.png", "wb") as f:
            f.write(img_data)
        logger.info("Graph visualization saved successfully to 'etl_analyst_graph.png'")
    except Exception as e:
        logger.warning(f"Could not save graph visualization: {e}")

    # Initialize State
    initial_state = {
        "messages": [HumanMessage(
            content="I want to extract the data from the API endpoint '[https://pokeapi.co/api/v2/pokemon](https://pokeapi.co/api/v2/pokemon)' "
                    "and save it to data/extract folder in the csv folder"
        )],
        "iterations": 0,
        "retry_count": 0
    }

    logger.info("Starting ETL Analyst Graph Execution...")
    
    response = etl_analyst.invoke(initial_state)
    
    print("\n" + "="*50)
    print("FINAL RESPONSE")
    print("="*50)
    print(response["messages"][-1].content)