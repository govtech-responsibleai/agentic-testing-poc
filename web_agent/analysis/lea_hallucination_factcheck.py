import math
import os
from pathlib import Path
import threading
import pandas as pd
import json
from tqdm.auto import tqdm
from analysis.factchecking import HallucinationFactChecker
from concurrent.futures import ThreadPoolExecutor
from fire import Fire
from dotenv import load_dotenv, find_dotenv

from analysis.llm_client import LLMClient

# def process_row(row_data, output_dir):
#     question = row_data["question"]
#     answer = row_data["answer"]
#     context = row_data["context"]
#     id = row_data["id"]
#     # try:
#     result = fact_checker.run(question, answer, context)

#     # fix decoding error
#     try:
#         results_data = json.loads(result)
#         with open(f"{output_dir}/hallucination_fact_check_results_{id}.json", "w") as f:
#             json.dump({"id": id, "question": question, "answer": answer, "context": context, "result": results_data}, f)
#     except json.JSONDecodeError as e:
#         print(f"Error decoding JSON for question: {result[:30]}... - {str(e)}")
#         with open(f"{output_dir}/hallucination_fact_check_results_{id}.json", "w") as f:
#             json.dump({"id": id, "question": question, "answer": answer, "context": context, "result": result}, f)
   
 
def main(input_file="data/analysis/hd_fc_by_record.csv", output_folder="data/output/hallucination_factchecking/records", start_index=0, end_index=None, batch_size=10):
    """Main function to run the fact checking agent."""
    load_dotenv(find_dotenv())
    model_config = {
        "MODEL_NAME": os.getenv("MODEL_NAME"),
        "API_KEY": os.getenv("OPENAI_API_KEY"),
        "BASE_URL": os.getenv("OPENAI_BASE_URL"),
    }
    llm_client = LLMClient(model_config)
    fact_checker = HallucinationFactChecker(llm_client)

    
    
    output_folder_path = Path(output_folder)
    output_folder_path.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_file)
    end_index = end_index if end_index is not None else len(df)
    print(f"Processing rows {start_index} to {end_index}")

    # Process in batches of 10
    num_batches = math.ceil((end_index - start_index) / batch_size)
    
    semaphore = threading.Semaphore(10)

    def process_single_row(row_data):
        with semaphore:
            row_num = row_data['id']
            try:
                result = fact_checker.run(row_data['question'], row_data['answer'], row_data['context'])
                with (output_folder_path / f"results_{row_num}.json").open("w") as f:
                    json.dump({
                        "id": row_num, 
                        "question": row_data['question'], 
                        "answer": row_data['answer'], 
                        "result": result
                    }, f)
            except Exception as e:
                print(f"Error processing question: {row_num}... - {str(e)}")
                with (output_folder_path / "errors.jsonl").open("a") as f:
                    f.write(json.dumps({
                        "id": row_num, 
                        "question": row_data['question'], 
                        "answer": row_data['answer'], 
                        "error": str(e)
                    }))
                    f.write("\n")

    for batch_num in tqdm(range(num_batches), desc="Processing batches"):
        batch_start = start_index + (batch_num * batch_size)
        batch_end = min(batch_start + batch_size, end_index)
        batch = df.iloc[batch_start:batch_end]
        
        batch_data = [{
            "id": index,
            "question": row["question"],
            "answer": row["answer"],
            "context": row["context"]
        } for index, row in batch.iterrows()]
        
        # Process batch with threading
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            list(tqdm(
                executor.map(process_single_row, batch_data),
                total=len(batch_data),
                desc=f"Processing batch {batch_num+1}/{num_batches}"
            ))

if __name__ == "__main__":
    Fire(main)