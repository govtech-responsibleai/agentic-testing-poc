import os
import json
import pandas as pd
import fire
from tqdm.auto import tqdm
from dotenv import load_dotenv, find_dotenv
from analysis.llm_client import LLMClient
from analysis.factchecking_agent import FactCheckingAgent
import concurrent.futures
import threading
from functools import partial


def run_factcheck(df: pd.DataFrame = None, start_idx: int = 0, end_idx: int = None, output_dir: str = None):
    """Main function to run the fact checking agent."""
    load_dotenv(find_dotenv())
    model_config = {
        "MODEL_NAME": os.getenv("MODEL_NAME"),
        "API_KEY": os.getenv("OPENAI_API_KEY"),
        "BASE_URL": os.getenv("OPENAI_BASE_URL"),
    }
    llm_client = LLMClient(model_config)
    factchecking_agent = FactCheckingAgent(llm_client)
    if end_idx is None:
        end_idx = len(df)
    df = df.iloc[start_idx:end_idx]
    
    # Create a semaphore to limit concurrent executions
    semaphore = threading.Semaphore(10)
    
    def process_claim(row, factchecking_agent):
        # Acquire the semaphore
        with semaphore:
            question_id = row["id"]
            claim_id = row["claim_idx"]
            claim = row["claim_text"]
            claim_check_result = factchecking_agent.run(checkworthy_claims=[claim])
            try:
                with open(f"{output_dir}/factcheck_result_{question_id}_{claim_id}.json", "w") as f:
                    json.dump({"question_id": question_id, "claim_id": claim_id, "claim": claim, "factcheck_result": claim_check_result}, f)
            except json.JSONDecodeError as e:
                print(f"Error in fact checking: {str(e)}")
                with open(f"{output_dir}/factcheck_result_{question_id}_{claim_id}.json", "w") as f:
                    f.write(claim_check_result)
    
    # Convert DataFrame to list of rows
    rows = [row for _, row in df.iterrows()]
    
    # Process in batches of 100
    batch_size = 100
    for i in tqdm(range(0, len(rows), batch_size), desc="Processing batches"):
        batch = rows[i:i+batch_size]
        
        # Create a partial function with the factchecking_agent already set
        process_func = partial(process_claim, factchecking_agent=factchecking_agent)
        
        # Process the batch in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            list(executor.map(process_func, batch))


def factcheck_hallucination_failures(start_idx=0, end_idx=100):
    # check hallucination failures
    df = pd.read_csv("data/output/hallucination_factchecking/consolidated/hallucination_fail_df.csv")
    output_dir = "data/output/hallucination_factchecking/hallucination_fail_fact_check_records"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    run_factcheck(df=df, start_idx=start_idx, end_idx=end_idx, output_dir=output_dir)

def factcheck_factcheck_failures(start_idx=0, end_idx=100):
    # check hallucination failures
    df = pd.read_csv("data/output/hallucination_factchecking/consolidated/factuality_fail_df.csv")
    output_dir = "data/output/hallucination_factchecking/factcheck_json_fail_fact_check_records"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # filter for failed to parse response
    df = df[df["reasoning"] == "['Failed to parse response']"]

    run_factcheck(df=df, start_idx=start_idx, end_idx=end_idx, output_dir=output_dir)


def main(start_idx=0, end_idx=None):
    # factcheck_hallucination_failures(start_idx=start_idx, end_idx=end_idx)
    factcheck_factcheck_failures(start_idx=start_idx, end_idx=end_idx)

if __name__ == "__main__":
    fire.Fire(main)