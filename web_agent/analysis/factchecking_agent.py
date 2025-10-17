# Standard library imports
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, TypedDict

# Third-party imports
import pandas as pd
from dotenv import find_dotenv, load_dotenv
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, Graph
from langgraph.prebuilt import create_react_agent
from tenacity import retry, retry_if_exception_type, stop_after_attempt
from tqdm.auto import tqdm

# Local imports
from analysis.factchecking import FactCheckResult
from analysis.llm_client import LLMClient
from analysis.prompts import factcheck_with_search_agent_system_prompt
from analysis.tools.ddg_tool import RetryDuckDuckGoSearchResults
from analysis.tools.visit_page_tool import fetch_url_content


log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logger = logging.getLogger("factcheck")
logger.setLevel(logging.INFO)
log_file = os.path.join(log_dir, f"factcheck_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
file_handler = logging.FileHandler(log_file)
logger.addHandler(file_handler)

# Class for factchecking agent only
class GraphState(TypedDict):
    checkworthy_claims: List[str]
    factcheck_results: Dict[str, Any]
    search_results: Dict[str, List[Dict[str, str]]]
    final_output: Dict[str, Any]

class FactCheckingAgent:
    """Main class for performing fact checking operations."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize the fact checker with necessary components."""
        self.llm_client = llm_client
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> Graph:
        """Create and compile the fact checking workflow graph."""
        workflow = Graph()
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_state)
        workflow.add_node("factuality_check", self._factuality_check_node)
        workflow.add_node("generate_report", self._generate_report_node)
        
        # Add edges
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "factuality_check")
        workflow.add_edge("factuality_check", "generate_report")
        workflow.add_edge("generate_report", END)
        
        return workflow.compile()
    
    def _initialize_state(self, state: Dict[str, Any]) -> GraphState:
        """Initialize the state with the input data."""
        input_data = state.get("input", {})
        return {
            "checkworthy_claims": input_data.get("checkworthy_claims", []),
            "factcheck_results": {},
            "search_results": {},
            "final_output": {}
        }

    def _factuality_check_node(self, state: GraphState) -> GraphState:
            """Check the factuality of claims using web search."""
            factcheck_results = {}
            
            for claim in state["checkworthy_claims"]:
                result = self._factuality_check(claim)
                factcheck_results[claim] = result
            
            return {**state, "factcheck_results": factcheck_results}

    @retry(stop=stop_after_attempt(3), retry=retry_if_exception_type(OutputParserException))
    def _search_and_check(self, claim: str) -> Dict[str, Any]:
        """Search and check the factuality of a single claim using web search."""
        memory = MemorySaver()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        search_agent = create_react_agent(
            self.llm_client.llm,
            tools=[RetryDuckDuckGoSearchResults(output_format="list"), fetch_url_content],
            checkpointer=memory,
            prompt=factcheck_with_search_agent_system_prompt
        )


        config = {"configurable": {"thread_id": timestamp}}
        agent_result = search_agent.invoke(
            input={
                "messages": [
                    {"role": "user", "content": f"This is the claim which you need to verify: {claim}"}
                ]
            },
            config=config
        )
        all_messages = agent_result["messages"]
            

        logger.info(f"Claim: {claim}")
        logger.info(all_messages)
        response = agent_result["messages"][-1]
                    
        parser = JsonOutputParser(pydantic_object=FactCheckResult)
        result = parser.parse(response.content)
                                
        return result
        
        

    def _factuality_check(self, claim: str) -> Dict[str, Any]:
        """Check the factuality of a single claim using web search."""
        try:
            result = self._search_and_check(claim)
            return result
        except Exception as e:
            logger.error(f"Error in fact checking: {str(e)}")
            return {
                "REASONING": [f"Failed to get valid JSON response after 3 attempts"],
                "LINKS": [],
                "SCORE": "FAIL"
            }


    def _generate_report_node(self, state: GraphState) -> GraphState:
        """Generate the final report."""
        final_output = self._generate_final_report(
            state["checkworthy_claims"],
            state["factcheck_results"],
        )
        return {**state, "final_output": final_output}
    

    def _generate_final_report(
        self,
        checkworthy_claims: List[str],
        factcheck_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate a final comprehensive report of the fact checking process."""
        # Prepare the claims check data
        claims_check = []
        
        for claim in checkworthy_claims:            
            claim_data = {"check_type": "factuality"}
            if claim in factcheck_results:
                claim_data["reasoning"] = factcheck_results[claim]["REASONING"]
                if "LINKS" in factcheck_results[claim]:
                    claim_data["links"] = factcheck_results[claim]["LINKS"]
                else:
                    claim_data["links"] = []
                claim_data["score"] = factcheck_results[claim]["SCORE"]
            else:
                claim_data["reasoning"] = ["No factuality check performed for this claim"]
                claim_data["score"] = "NA"
            
                
            claims_check.append(claim_data)
        
        # Compile the final report
        final_report = {
            "claims_check": claims_check
        }
        
        return final_report
    


    def run(self, checkworthy_claims: List[str]) -> Dict[str, Any]:
        """Run the fact checking workflow."""
        result = self.workflow.invoke({
            "input": {
                "checkworthy_claims": checkworthy_claims
            }
        })
        return result["final_output"]
    


