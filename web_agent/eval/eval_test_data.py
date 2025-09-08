from pathlib import Path
import requests
from tqdm import tqdm
from pathlib import Path
import json

headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json',
}   

def main():
    input_dir_path = Path("/home/watsonchua/sls-lea-evaluation/data/eval/answer_set")
    output_dir_path = Path("/home/watsonchua/sls-lea-evaluation/data/eval/results_set")
    output_dir_path.mkdir(parents=True, exist_ok=True)
    all_files = list(input_dir_path.glob("*.json"))
    for file in tqdm(all_files):
        print(file)
        if Path(output_dir_path / f"{file.stem}.json").exists():
            print(f"Skipping {file} because it already exists")
            continue

        with file.open("r") as f:
            data = json.load(f)
        
        final_results = {}
        final_results['question_from_context_answer_from_context'] = []
        final_results['question_from_context_answer_from_search'] = []
        final_results['question_not_from_context_answer_from_search'] = []
        final_results['question_not_from_context_answer_not_from_search'] = []


        context = data['context']
        for final_result_keys in ["question_from_context_answer_from_context", "question_from_context_answer_from_search", "question_not_from_context_answer_from_search", "question_not_from_context_answer_not_from_search"]:
            for question_answer_pair in tqdm(data[final_result_keys], desc=f"Processing {final_result_keys}"):
                json_data = {
                    'question': question_answer_pair["question"],
                    'answer': question_answer_pair["answer"],
                    'context': context
                }

                response = requests.post(
                    'https://sls-lea-fastapi-67614827903.asia-southeast1.run.app/factcheck',
                    headers=headers,
                    json=json_data,
                )

                try:
                    result_json = response.json()
                    final_results[final_result_keys].append(result_json)
                except Exception as e:
                    print(f"Error parsing response for {question_answer_pair['question']}: {e}")
                    continue

        
        with (output_dir_path / f"{file.stem}.json").open("w") as f:
            json.dump(final_results, f)  


if __name__ == "__main__":
    main()
