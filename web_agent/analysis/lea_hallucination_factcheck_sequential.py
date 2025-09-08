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
import requests


   
 
def main(input_file="data/analysis/hd_fc_by_record.csv", output_folder="data/output/hallucination_factchecking/records", start_index=0, end_index=None):
    """Main function to run the fact checking agent."""
    load_dotenv(find_dotenv())
        
    output_folder_path = Path(output_folder)
    output_folder_path.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_file)
    end_index = end_index if end_index is not None else len(df)
    print(f"Processing rows {start_index} to {end_index}")

    df = df.iloc[start_index:end_index]
    
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
    }

    for index, row in tqdm(df.iterrows(), total=len(df)):
        json_data = {
            'question': row["question"],
            'answer': row["answer"],
            'context': row["context"]
        }

        response = requests.post(
            'https://sls-lea-fastapi-67614827903.asia-southeast1.run.app/factcheck',
            headers=headers,
            json=json_data,
        )

        with (output_folder_path / f"results_{index}.json").open("w") as f:
            json.dump(response.json(), f)        

if __name__ == "__main__":
    Fire(main)