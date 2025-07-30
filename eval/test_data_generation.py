from datetime import datetime
import json
import os
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from analysis.llm_client import LLMClient
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from typing import List
from pydantic import BaseModel, Field
from tqdm import tqdm
from langgraph.prebuilt import create_react_agent
from langchain_community.tools import DuckDuckGoSearchResults
from analysis.tools.visit_page_tool import fetch_url_content
from langgraph.checkpoint.memory import MemorySaver
# from analysis.tools.ddg_tool import DuckDuckGoSearchResultsTool

json_parser = JsonOutputParser()

question_generation_system_prompt = """
    You are a helpful assistant that generates question and answer for a test.
    You will be given a context and you need to generate questions and answers from the context.
    Follow these instructions specifically:
    - Generate 10 questions which can be answered by the context.
    - Generate 10 questions on the topic of the context which cannot be answered by the context.
    - For questions which cannot be answered by the context, make sure they are not too vague or broad, and can be answered using factual information from the internet or wikipedia. For example, do not ask questions on opinions which are subjective, or exact numbers which can differ across sources and time. Focus on asking factually verifiable questions.



    Return the questions and answers in JSON in the following format:
    {
        "question_answerable_by_context": [
           question1, question2, ...
        ],
        "question_not_answerable_by_context": [
            question1, question2, ...
        ],
    }

    The output should be in JSON format parsed by the JSON decoder. Do not include any other text in the output.
    """

question_answering_from_context_system_prompt = """
    You are a helpful assistant that generates answers to questions from a given context.
    You will be given a context and a question.
    You need to generate an answer to the question from the context.
    IMPORTANT: Use only information in the context to answer the question. Give a concise and relevant answer.
    
    Return the answers in JSON in the following format:
    {
        "answer": answer_to_question
    }

    The output should be in JSON format parsed by the JSON decoder. Do not include any other text in the output.        
"""

question_answering_with_search_system_prompt = """
    You are a helpful assistant that generates answers to questions.
    You are given tools to search the internet and fetch the content of a webpage.
    You need to generate an answer that is factual to the question. Factual answers are those which can be verified on news websites and wikipedia, or reputable sources.
    You need to use the search and, if necessary, web retrieval, tools to find the most relevant information to the question.
    Return the answers in JSON in the following format:
    {
        "answer": answer_to_question
    }

    The output should be in JSON format parsed by the JSON decoder. Do not include any other text in the output.        
"""

counterfactual_answering_system_prompt = """
    You are a helpful assistant. Given a question with a correct answer, your job is to make the answer counterfactual so that it can be given to students as a choice of which is correct and which is wrong.
    The counterfactual answer should be incorrect, and totally opposite to the correct answer. Each claim in the answer has to be obviously counterfactual so that students can easily identify the correct answer.
    You do not need to provide the correct answer, just the counterfactual answer.
    Return the counterfactual answer in JSON in the following format:
    {
        "answer": counterfactual_answer_to_question
    }

    The output should be in JSON format parsed by the JSON decoder. Do not include any other text in the output.        
"""

class AnswerResult(BaseModel):
    answer: str = Field(description="Answer to a question")

class QuestionFromContextResult(BaseModel):
    question_answerable_by_context: List[str] = Field(description="List of questions that can be answered by the context")
    question_not_answerable_by_context: List[str] = Field(description="List of questions that cannot be answered by the context")



def generate_answers_from_web(llm_client: LLMClient, question: str, use_out_of_context_answers: str=None, context: str=None):
    additional_instructions = ""
    if use_out_of_context_answers:
        if context is None:
            raise ValueError("Context is required when use_out_of_context_answers is True")
        additional_instructions = f"You need to generate an answer that is factually correct according to the search results, but not found in the context. Claims in the answer should not be found in the context. This is the context: \n\n {context}"
    
    
    memory = MemorySaver()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    config = {"configurable": {"thread_id": timestamp}}


    search_agent = create_react_agent(
        llm_client.llm,
        # tools=[DuckDuckGoSearchResultsTool(output_format="list"), fetch_url_content],
        tools=[DuckDuckGoSearchResults(output_format="list"), fetch_url_content],
        checkpointer=memory,
        prompt=question_answering_with_search_system_prompt
    )

    result = search_agent.invoke(
        input={
            "messages": [
                {"role": "user", "content": f"{additional_instructions} \n\n This is the question: \n\n {question}"}
            ]
        },
        config=config
    )

    return result["messages"][-1]
    
   
def generate_counterfactual_answers(llm_client: LLMClient, question: str, answer: str):        
    result = llm_client.invoke([
        {"role": "system", "content": counterfactual_answering_system_prompt},
        {"role": "user", "content": f"This is the question: \n\n {question} \n\n This is the answer: \n\n {answer}"},
    ])

    return result

def generate_answers_from_context(llm_client: LLMClient, question: str, context: str=None):        
    result = llm_client.invoke([
        {"role": "system", "content": question_answering_from_context_system_prompt},
        {"role": "user", "content": f"This is the context: \n\n {context}. \n\n Now, answer the following question: \n\n {question}"},
    ])

    return result





def generate_in_and_out_context_questions(llm_client: LLMClient, context: str):
    
    return llm_client.invoke([
        {"role": "system", "content": question_generation_system_prompt},
        {"role": "user", "content": f"This is the context: \n\n {context}"},
    ])


def generate_questions(llm_client: LLMClient, output_dir_path: Path):
    with open("/home/watsonchua/sls-assistant-evaluation/data/discussion_topics_with_llm_content.jsonl", "r") as f:
        lines = f.readlines()
    
    for line in tqdm(lines):
        line_id = json.loads(line)["id"]
        context = json.loads(line)["knowledge_base_content"]    
        result = generate_in_and_out_context_questions(llm_client, context=context)
        
        result_json = json_parser.parse(result.content)
        result_json['context'] = context
        if 'question_answerable_by_context' not in result_json or 'question_not_answerable_by_context' not in result_json:
            print(f"Line {line_id} does not have the correct keys.")
            continue
        if len(result_json['question_answerable_by_context']) != 10 or len(result_json['question_not_answerable_by_context']) != 10:
            print(f"Line {line_id} has {len(result_json.question_answerable_by_context)} questions that can be answered by the context and {len(result_json.question_not_answerable_by_context)} questions that cannot be answered by the context")
        with open(output_dir_path / f"questions_{line_id}.json", "w") as f:
            json.dump(result_json, f)


def generate_answers(llm_client: LLMClient, question_input_dir: Path, answer_output_dir: Path, overwrite: bool=False):
    answer_json_parser = JsonOutputParser(pydantic_object=AnswerResult)

    question_files = list(question_input_dir.glob("questions_*.json"))




    for question_file in tqdm(question_files):
        if not overwrite and Path(answer_output_dir / f"answers_{question_file.stem}.json").exists():
            print(f"Skipping {question_file} because it already exists")
            continue

        final_results = {}
        final_results['question_from_context_answer_from_context'] = []
        final_results['question_from_context_answer_from_search'] = []
        final_results['question_not_from_context_answer_from_search'] = []
        final_results['question_not_from_context_answer_not_from_search'] = []


        with open(question_file, "r") as f:
            data = json.load(f)
        
        context = data['context']
        final_results['context'] = context
        questions_answerable_by_context = data['question_answerable_by_context']
        questions_not_answerable_by_context = data['question_not_answerable_by_context']



        for q_no, question in enumerate(tqdm(questions_answerable_by_context, desc="Generating answers for in-context questions")):
            # question from context, answer from context

            result = generate_answers_from_context(llm_client, question, context)
            try:
                result_json = answer_json_parser.parse(result.content)
                result_json['question'] = question
                final_results['question_from_context_answer_from_context'].append(result_json)
            except OutputParserException as e:
                print(f"Error parsing answer for question {question}: {e}")
            except TypeError as e:
                print(f"Error parsing answer for question {question}: {e}")
                
                
            

            # question from context, answer from search
            result = generate_answers_from_web(llm_client, question, use_out_of_context_answers=True, context=context)
            try:
                result_json = answer_json_parser.parse(result.content)
                result_json['question'] = question
                final_results['question_from_context_answer_from_search'].append(result_json)
            except OutputParserException as e:
                print(f"Error parsing answer for question {question}: {e}")
                continue
            except TypeError as e:
                print(f"Error parsing answer for question {question}: {e}")
                continue


        for q_no, question in enumerate(tqdm(questions_not_answerable_by_context, desc="Generating answers for out-of-context questions")):
            # question not from context, correct answer from search
            result = generate_answers_from_web(llm_client, question, use_out_of_context_answers=False)
            try:
                result_json = answer_json_parser.parse(result.content)
                result_json['question'] = question
                final_results['question_not_from_context_answer_from_search'].append(result_json)
            except OutputParserException as e:
                print(f"Error parsing answer for question {question}: {e}")
                continue
            except TypeError as e:
                print(f"Error parsing answer for question {question}: {e}")
                continue
            

            correct_answer = result_json['answer']
            # question not from context, wrong answer from search
            result = generate_counterfactual_answers(llm_client, question, correct_answer)
            try:
                result_json = answer_json_parser.parse(result.content)
                result_json['question'] = question
                final_results['question_not_from_context_answer_not_from_search'].append(result_json)
            except OutputParserException as e:
                print(f"Error parsing answer for question {question}: {e}")
                continue
            except TypeError as e:
                print(f"Error parsing answer for question {question}: {e}")
                continue

        

        with open(answer_output_dir / f"answers_{question_file.stem}.json", "w") as f:
            json.dump(final_results, f)


def main():
    # model_config = {
    #     "MODEL_NAME": "",
    #     "API_KEY": "",
    #     "BASE_URL": "http://100.66.92.93:9099/v1",
    # }

    load_dotenv(find_dotenv())
    model_config = {
        "MODEL_NAME": os.getenv("MODEL_NAME"),
        "API_KEY": os.getenv("OPENAI_API_KEY"),
        "BASE_URL": os.getenv("OPENAI_BASE_URL"),
    }

    
    llm_client = LLMClient(model_config)

    question_output_dir = Path("/home/watsonchua/sls-lea-evaluation/data/eval/question_set/")
    question_output_dir.mkdir(parents=True, exist_ok=True)
    # generate_questions(llm_client, question_output_dir)

    answer_output_dir = Path("/home/watsonchua/sls-lea-evaluation/data/eval/answer_set/")
    answer_output_dir.mkdir(parents=True, exist_ok=True)
    generate_answers(llm_client, question_output_dir, answer_output_dir)

    


if __name__ == "__main__":
    main()
