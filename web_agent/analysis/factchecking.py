# Standard library imports
import asyncio
import json
import logging
import os
import traceback
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, Tuple, TypedDict

# Third-party imports
from dotenv import find_dotenv, load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables.graph import MermaidDrawMethod
from langfuse.callback import CallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, Graph
from langgraph.prebuilt import create_react_agent

# Local imports
from analysis.llm_client import LLMClient
from analysis.prompts import (
    answer_decomposition_prompt_template,
    checkworthy_prompt_template,
    fact_checking_from_sources_prompt_template,
    factcheck_with_search_agent_system_prompt,
    hallucination_detection_prompt_template,
    question_detection_prompt_template,
)
from analysis.pydantic_models import (
    ClaimVerifiableResult,
    FactCheckResult,
    HallucinationResult,
    QuestionAnswerableResult,
)
from analysis.tools.ddg_tool import RetryDuckDuckGoSearchResults
from analysis.tools.visit_page_tool import fetch_url_content

load_dotenv(find_dotenv())

langfuse_handler = CallbackHandler()


log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logger = logging.getLogger("factcheck")
logger.setLevel(logging.INFO)
log_file = os.path.join(log_dir, f"factcheck_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
file_handler = logging.FileHandler(log_file)
logger.addHandler(file_handler)

# State definition
class FactCheckState(TypedDict):
    question: str
    answer: str
    context: str
    claims: List[str]
    checkworthy_claims: List[str]
    answerable_by_context: bool
    hallucination_results: Dict[str, Any]
    factcheck_results: Dict[str, Any]
    search_results: Dict[str, List[Dict[str, str]]]
    final_output: Dict[str, Any]



class HallucinationFactChecker:
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
        workflow.add_node("decompose_answer", self._decompose_answer_node)
        workflow.add_node("check_claims_verifiable", self._check_claims_verifiable_node)
        workflow.add_node("check_question_answerable", self._check_question_answerable_node)
        workflow.add_node("faithfulness_check", self._hallucination_check_node)
        workflow.add_node("factuality_check", self._factuality_check_node)
        workflow.add_node("generate_report", self._generate_report_node)
        
        # Add edges
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "decompose_answer")
        workflow.add_edge("decompose_answer", "check_claims_verifiable")
        workflow.add_edge("check_claims_verifiable", "check_question_answerable")
        
        # Conditional routing
        workflow.add_conditional_edges(
            "check_question_answerable",
            self._route_claims,
            {
                "faithfulness_check": "faithfulness_check",
                "factuality_check": "factuality_check"
            }
        )
        
        # do factuality checks for hallucination failed claims
        workflow.add_conditional_edges(
            "faithfulness_check",
            self._route_hallucination_failed_claims,
            {
                "factuality_check": "factuality_check",
                "generate_report": "generate_report"
            }
        )

        # workflow.add_edge("faithfulness_check", "generate_report")
        workflow.add_edge("factuality_check", "generate_report")
        workflow.add_edge("generate_report", END)
        
        return workflow.compile().with_config({"callbacks": [langfuse_handler]})
    
    def _initialize_state(self, state: Dict[str, Any]) -> FactCheckState:
        """Initialize the state with the input data."""
        input_data = state.get("input", {})
        return {
            "question": input_data.get("question", ""),
            "answer": input_data.get("answer", ""),
            "context": input_data.get("context", ""),
            "claims": [],
            "checkworthy_claims": [],
            "hallucination_failed_claims": [],
            "factuality_claims": [],
            "answerable_by_context": False,
            "hallucination_results": {},
            "factcheck_results": {},
            "search_results": {},
            "final_output": {}
        }
    
    def _decompose_answer_node(self, state: FactCheckState) -> FactCheckState:
        """Extract individual claims from the answer."""
        claims = self._decompose_answer(state["question"], state["answer"])
        return {**state, "claims": claims}
    
    def _check_claims_verifiable_node(self, state: FactCheckState) -> FactCheckState:
        """Check which claims are verifiable."""
        checkworthy_claims = [
            claim for claim in state["claims"]
            if self._check_claim_verifiable(claim).get("CHECKWORTHY") == "PASS"
        ]
        return {**state, "checkworthy_claims": checkworthy_claims}
    
    def _check_question_answerable_node(self, state: FactCheckState) -> FactCheckState:
        """Check if the question is answerable by the context."""
        if not state["context"]:
            return {**state, "answerable_by_context": False}
        
        result = self._check_question_answerable(state["question"], state["context"])
        return {**state, "answerable_by_context": result.get("SCORE") == "PASS"}
    
    def _route_claims(self, state: FactCheckState) -> str:
        """Route to the appropriate node based on whether the question is answerable by context."""
        return "faithfulness_check" if state["answerable_by_context"] else "factuality_check"
    
    def _route_hallucination_failed_claims(self, state: FactCheckState) -> str:
        """Route to the appropriate node based on whether the question is answerable by context."""
        return "factuality_check" if state["hallucination_failed_claims"] else "generate_report"
    
    def _hallucination_check_node(self, state: FactCheckState) -> FactCheckState:
        """Check for hallucinations in the claims based on the context."""
        hallucination_results = {
            claim: self._check_hallucination(state["question"], claim, state["context"])
            for claim in state["checkworthy_claims"]
        }

        hallucination_failed_claims = [claim for claim, result in hallucination_results.items() if result["SCORE"] == "FAIL"]
        return {**state, "hallucination_results": hallucination_results, "hallucination_failed_claims": hallucination_failed_claims}
    
    def _factuality_check_node(self, state: FactCheckState) -> FactCheckState:
        """Check the factuality of claims using web search."""
        factcheck_results = {}
        
        # check only hallucination failed claims if any
        if state["hallucination_failed_claims"]:
            claims_to_check = state["hallucination_failed_claims"]
        # else check all checkworthy claims
        else:
            claims_to_check = state["checkworthy_claims"]

        for claim in claims_to_check:
            result = self._factuality_check(claim)
            factcheck_results[claim] = result
        
        return {**state, "factcheck_results": factcheck_results}
    
    def _factuality_check(self, claim: str) -> Dict[str, Any]:
        """Check the factuality of a single claim using web search."""
        memory = MemorySaver()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        search_agent = create_react_agent(
            self.llm_client.llm,
            tools=[RetryDuckDuckGoSearchResults(output_format="list"), fetch_url_content],
            checkpointer=memory,
            prompt=factcheck_with_search_agent_system_prompt
        )
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            # try:
            config = {"configurable": {"thread_id": timestamp}, "recursion_limit": 10}
            try:
                agent_result = search_agent.invoke(
                    input={
                        "messages": [
                            {"role": "user", "content": f"This is the claim which you need to verify: {claim}"}
                        ]
                    },
                    config=config
                )
            except GraphRecursionError:
                # Handle recursion limit error
                logger.warning(f"GraphRecursionError encountered for claim: {claim}")
                return {
                    "REASONING": ["The fact-checking process exceeded the recursion limit. The claim may be too complex to verify."],
                    "LINKS": [],
                    "SCORE": "ERROR"
                }
            all_messages = agent_result["messages"]
            

            logger.info(f"Claim: {claim}")
            logger.info(all_messages)
            response = agent_result["messages"][-1]
            
            # Try to parse the response as JSON first
            try:
                json.loads(response.content)
            except json.JSONDecodeError:
                print(f"Invalid JSON format, retrying... (attempt {retry_count + 1}/{max_retries})")
                retry_count += 1
                continue
            
            parser = JsonOutputParser(pydantic_object=FactCheckResult)
            result = parser.parse(response.content)
            
            # Validate required fields
            if not all(key in result for key in ["REASONING", "SCORE"]):
                print(f"Missing required fields, retrying... (attempt {retry_count + 1}/{max_retries})")
                retry_count += 1
                continue
                
            if result["SCORE"] not in ["PASS", "FAIL"]:
                print(f"Invalid SCORE value, retrying... (attempt {retry_count + 1}/{max_retries})")
                retry_count += 1
                continue
            
            return result
                        
        return {
            "REASONING": [f"Failed to get valid JSON response after {max_retries} attempts"],
            "LINKS": [],
            "SCORE": "ERROR"
        }
    
    def _generate_report_node(self, state: FactCheckState) -> FactCheckState:
        """Generate the final report."""
        final_output = self._generate_final_report(
            state["question"],
            state["answer"],
            state["context"],
            state["claims"],
            state["checkworthy_claims"],
            state["answerable_by_context"],
            state["hallucination_results"],
            state["factcheck_results"],
        )
        return {**state, "final_output": final_output}



    def _check_question_answerable(self, question: str, context: str) -> Dict[str, Any]:   
        """Check if a question is answerable by the given context."""
        prompt = question_detection_prompt_template.format(question=question, context=context)
        
        def _invoke():
            return self.llm_client.invoke([HumanMessage(content=prompt)])
        
        try:
            response = self.llm_client.call_with_retry(_invoke)
            parser = JsonOutputParser(pydantic_object=QuestionAnswerableResult)
            result = parser.parse(response.content)
            return result
        except Exception as e:
            # Fallback if parsing fails
            print(f"Failed to parse response: {str(e)}")
            return {
                "REASONING": "Failed to parse response",
                "SCORE": "ERROR"
            }

    def _check_claim_verifiable(self, claim: str) -> Dict[str, str]:
        """Check if a claim is verifiable (not an opinion or expression)."""
        prompt = checkworthy_prompt_template.format(claim=claim)
        
        def _invoke():
            return self.llm_client.invoke([HumanMessage(content=prompt)])
        
        try:
            response = self.llm_client.call_with_retry(_invoke)
            parser = JsonOutputParser(pydantic_object=ClaimVerifiableResult)
            result = parser.parse(response.content)
            return result
        except Exception as e:
            # Fallback if parsing fails
            print(f"Failed to parse response: {str(e)}")
            return {"CHECKWORTHY": "ERROR"}

    def _check_hallucination(self, question: str, claim: str, context: str) -> Dict[str, Any]:
        """Check if an answer contains hallucinations based on the given context."""
        prompt = hallucination_detection_prompt_template.format(
            question=question, 
            claim=claim, 
            context=context
        )
        
        def _invoke():
            return self.llm_client.invoke([HumanMessage(content=prompt)])
        
        try:
            response = self.llm_client.call_with_retry(_invoke)
            parser = JsonOutputParser(pydantic_object=HallucinationResult)
            result = parser.parse(response.content)
            return result
        except Exception as e:
            # Fallback if parsing fails
            print(f"Failed to parse response: {str(e)}")
            return {
                "REASONING": ["Failed to parse response"],
                "SCORE": "ERROR"
            }

    def _fact_check_from_sources(self, claim: str, documents: str) -> Dict[str, Any]:
        """Check if a claim is factual based on provided documents."""
        prompt = fact_checking_from_sources_prompt_template.format(
            claim=claim,
            documents=documents
        )
        
        def _invoke():
            return self.llm_client.invoke([HumanMessage(content=prompt)])
        
        try:
            response = self.llm_client.call_with_retry(_invoke)
            parser = JsonOutputParser(pydantic_object=FactCheckResult)
            result = parser.parse(response.content)
            return result
        except Exception as e:
            # Fallback if parsing fails
            print(f"Failed to parse response: {str(e)}")
            return {
                "REASONING": ["Failed to parse response"],
                "SCORE": "ERROR"
            }

    def _decompose_answer(self, question: str, answer: str) -> List[str]:
        """Extract individual claims from a text."""
        prompt = answer_decomposition_prompt_template.format(question=question, answer=answer)
        
        def _invoke():
            return self.llm_client.invoke([HumanMessage(content=prompt)])
        
        try:
            response = self.llm_client.call_with_retry(_invoke)
            parser = JsonOutputParser()
            result = parser.parse(response.content)
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "CLAIMS" in result:
                return result["CLAIMS"]
            else:
                # If the structure is unexpected, try to extract from the raw text
                return [answer]
        except Exception as e:
            # Fallback if parsing fails
            print(f"Failed to parse claims: {str(e)}")
            return [answer]
        
    def _generate_final_report(
        self,
        question: str,
        answer: str,
        context: str,
        claims: List[str],
        checkworthy_claims: List[str],
        answerable_by_context: bool,
        hallucination_results: Dict[str, Any],
        factcheck_results: Dict[str, Any],
        # hallucination_failed_claims: List[str],
    ) -> Dict[str, Any]:
        """Generate a final comprehensive report of the fact checking process."""
        # Prepare the claims check data
        claims_check = []
        
        for claim in claims:
            claim_data = {
                "claim": claim,
                "checkworthy_reasoning": "This claim makes a factual statement that can be verified." if claim in checkworthy_claims else "This claim is an expression or opinion and cannot be verified.",
                "checkworthy": "PASS" if claim in checkworthy_claims else "FAIL"
            }
            
            # Using a list to store all checks for the claim
            if claim in checkworthy_claims:
                combined_score = "FAIL"
                
                if claim in hallucination_results:
                    claim_data["faithfulness_check"] = {                    
                        "reasoning" : hallucination_results[claim]["REASONING"],
                        "score" : hallucination_results[claim]["SCORE"]
                    }
                    combined_score = "PASS" if hallucination_results[claim]["SCORE"] == "PASS" else combined_score
                
                # double check for hallucination failed claims
                if claim in factcheck_results:
                    claim_data["factuality_check"] = {                    
                        "reasoning" : factcheck_results[claim]["REASONING"],
                        "links" : factcheck_results[claim]["LINKS"] if "LINKS" in factcheck_results[claim] else [],
                        "score" : factcheck_results[claim]["SCORE"]
                    }
                    combined_score = "PASS" if factcheck_results[claim]["SCORE"] == "PASS" else combined_score
                
                claim_data["final_score"] = combined_score
            
            else:
                # claim_data["check_type"] = "NA"
                # claim_data["reasoning"] = ["Claim is not checkworthy"]
                claim_data["final_score"] = "NA"
            
            claims_check.append(claim_data)
        # Compile the final report
        final_report = {
            "question": question,
            "answer": answer,
            "answerable_by_context": "PASS" if answerable_by_context else "FAIL",
            "claims_check": claims_check
        }
        
        return final_report

    
    
    def run(self, question: str, answer: str, context: str) -> Dict[str, Any]:
        """Run the fact checking workflow."""
        result = self.workflow.invoke({
            "input": {
                "question": question,
                "answer": answer,
                "context": context
            }
        })
        return result["final_output"]


def save_workflow_diagram(workflow: Graph, filename: str):
    """Save the workflow diagram as a PNG file."""
    graph_image = workflow.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
    with open(filename, "wb") as f:
        f.write(graph_image)

async def main(save_diagram: bool = False):
    """
    Main function to demonstrate the fact checking workflow.
    
    This function runs a sample fact checking operation and prints the results.
    """

    # Load environment variables
    load_dotenv(find_dotenv())
    model_config = {
        "MODEL_NAME": os.getenv("MODEL_NAME"),
        "API_KEY": os.getenv("OPENAI_API_KEY"),
        "BASE_URL": os.getenv("OPENAI_BASE_URL"),
    }
    # Sample data for testing
    # question = "That's interesting! But I wonder, what challenges does Singapore face when it comes to food security? Like, what makes it tough for them to keep everything stable?"
    # answer = "Singapore faces several challenges regarding food security. Its heavy reliance on food imports makes it vulnerable to global supply chain disruptions, geopolitical tensions, and trade restrictions. Additionally, limited land for agriculture constrains local food production. Climate change poses risks through unpredictable weather patterns, affecting food supply. Lastly, ensuring food affordability and nutritional diversity for all residents remains a significant challenge, especially for lower-income households. It's also tough because Singapore was a fishing village in its early days."
    # context = "Singapore faces significant challenges in ensuring food security due to its heavy reliance on food imports, which makes it particularly vulnerable to global supply chain disruptions, geopolitical tensions, and trade restrictions. With limited land available for agriculture, the country faces constraints in boosting local food production to reduce dependency on external sources. Additionally, climate change exacerbates these issues by introducing unpredictable weather patterns that can disrupt food supply chains. Ensuring food affordability and maintaining nutritional diversity for all residents, especially for lower-income households, further complicates the effort to achieve sustainable food security."
    question = "What is the capital of India?"
    answer = "India is a great place to visit! It is a country in South Asia. Its capital is New Delhi, and its largest city is Mumbai."
    context = "The capital of India is New Delhi."
    try:
        llm_client = LLMClient(model_config)

        # Initialize and run the fact checker
        hallucination_fact_checker = HallucinationFactChecker(llm_client)

        save_workflow_diagram(hallucination_fact_checker.workflow, "hallucination_factcheck_workflow.png")
        result = hallucination_fact_checker.run(question, answer, context)        
        print(json.dumps(result, indent=4))        
        
    except Exception as e:
        print(f"\nError during fact checking: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())
