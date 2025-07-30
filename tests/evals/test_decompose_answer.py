import os
import pytest
from dotenv import load_dotenv, find_dotenv
from rouge_score.rouge_scorer import RougeScorer
from analysis.factchecking import HallucinationFactChecker
from analysis.llm_client import LLMClient

load_dotenv(find_dotenv())

MODEL_CONFIG = {
    "MODEL_NAME": "gpt-4.1",
    "API_KEY": os.getenv("OPENAI_API_KEY"),
    "BASE_URL": os.getenv("OPENAI_API_BASE"),
}

# Each triple is (question, answer, expected_claims)
TRIPLES = [
    (
        "What is the capital of France?",
        "The capital of France is Paris.",
        ["The capital of France is Paris."]
    ),
    (
        "What is the capital of France?",
        "The capital of France is Paris. It has a population of 2.1 million people.",
        ["The capital of France is Paris.", "Paris has a population of 2.1 million people."]
    ),
    (
        "What is the capital of France?",
        "It is Paris where the Eiffel Tower is located.",
        ["The capital of France is Paris.", "The Eiffel Tower is in Paris."]
    ),
]

@pytest.fixture
def real_fact_checker():
    llm_client = LLMClient(MODEL_CONFIG)
    return HallucinationFactChecker(llm_client)

@pytest.mark.parametrize("question,answer,expected_claims", TRIPLES)
def test_decompose_answer_correct_number_of_claims(real_fact_checker, question, answer, expected_claims):
    result = real_fact_checker._decompose_answer(question, answer)
    assert len(result) == len(expected_claims)

@pytest.mark.parametrize("question,answer,expected_claims", TRIPLES)
def test_decompose_answer_rouge_score(real_fact_checker, question, answer, expected_claims):
    result = real_fact_checker._decompose_answer(question, answer)
    scorer = RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = [scorer.score(r, e)['rougeL'].fmeasure for r, e in zip(result, expected_claims)]
    assert min(scores) > 0.9
