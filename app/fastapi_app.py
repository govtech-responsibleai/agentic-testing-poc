import os
import traceback
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional
from dotenv import load_dotenv, find_dotenv
from analysis.llm_client import LLMClient
from analysis.factchecking import HallucinationFactChecker

# Load environment variables
load_dotenv(find_dotenv())

# Create FastAPI app
app = FastAPI(
    title="Fact Checking API",
    description="API for checking hallucinations and factuality in answers",
    version="1.0.0"
)

# Define request model
class FactCheckRequest(BaseModel):
    question: str = "What is the capital of India?"
    answer: str = "India is a great place to visit! It is a country in South Asia. Its capital is New Delhi, and its largest city is Mumbai."
    context: Optional[str] = "The capital of India is New Delhi."

# Define response model
class FactCheckResponse(BaseModel):
    result: Dict[str, Any]

@app.post("/factcheck", response_model=FactCheckResponse)
async def factcheck(request: FactCheckRequest = Body(...)):
    """
    Check the factuality of an answer given a question and optional context.
    
    Returns a detailed report of the fact checking process.
    """
    try:
        # Initialize LLM client
        model_config = {
            "MODEL_NAME": "azure/gpt-4o-eastus",
            "API_KEY": os.getenv("OPENAI_API_KEY"),
            "BASE_URL": os.getenv("OPENAI_BASE_URL"),
        }
        
        llm_client = LLMClient(model_config)
        
        # Initialize and run the fact checker
        hallucination_fact_checker = HallucinationFactChecker(llm_client)
        result = hallucination_fact_checker.run(
            request.question, 
            request.answer, 
            request.context
        )
        
        return FactCheckResponse(result=result)
        
    except Exception as e:
        error_msg = f"Error during fact checking: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Fact Checking API is running"}



