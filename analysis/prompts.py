question_detection_prompt_template = """
Given the following QUESTION and DOCUMENT, you must analyze the question and determine whether it can be answered using the information provided in the DOCUMENT.

Give your answer as a parsable JSON object with the keys "REASONING" and "SCORE" where SCORE is PASS or FAIL.

--
QUESTION (THIS DOES NOT COUNT AS BACKGROUND INFORMATION):
{question}

--
DOCUMENT:
{context}

--

{{"REASONING": "<your reasoning as bullet points>", "SCORE": "<PASS or FAIL>"}}
"""


checkworthy_prompt_template = """
    Given a claim or a statement, assess if it can be checked for factuality. For example, if a claim is an opinion or an expression, it cannot be checked for factuality.
    Give your answer in JSON format as follows:
    {{"CHECKWORTHY": "<PASS or FAIL>"}}

    This is the claim: {claim}
"""

# splitting_prompt_template = """
#     Given a text which can consist of one or more claims, split it into individual claims or statements.
#     Give your answer in JSON format as follows:
#     {{"CLAIMS": ["<individual claims>"]}}
# """

hallucination_detection_prompt_template="""
    
    Given the following QUESTION,DOCUMENT and CLAIM you must analyze the claim and determine whether the claim can be inferred from the contents of the DOCUMENT.
    
    The CLAIM must not offer new information beyond the context provided in the DOCUMENT.

    The CLAIM also must not contradict information provided in the DOCUMENT.

    IMPORTANT: The CLAIM does NOT need to cover all the claims in the DOCUMENT. 

    Output your final score by strictly following this format: "PASS" if the claim can be inferred from the DOCUMENT and "FAIL" if the claim cannot be inferred from the contents of the DOCUMENT.

    Show your reasoning.  Be concise in the reasoning and focus more on the failures, if any.

    --
    QUESTION (This does not count as background information):
    {question}

    --
    DOCUMENT:
    {context}

    --
    CLAIM:
    {claim}

    --

    Your output should be in JSON FORMAT with the keys "REASONING" and "SCORE".

    Ensure that the JSON is valid and properly formatted.

    {{"REASONING": ["<your reasoning as bullet points>"], "SCORE": "<PASS or FAIL>"}}
"""

factcheck_with_search_agent_system_prompt = """
You are a helpful assistant that can search the web for information, and get contents from the search results to verify a claim.

Given the following claim, search the web for information to verify the claim. Important: Search only on wikipedia and established news sites.

Give your reasons for your assessment of the claim by showing relevant snippets and urls which shows that the assessment is supported, for claims which are supported by the search results.

If you do not have enough information to make an assessment of the claim based on the search results snippets, you can use the visit page tool to get more content. 

IMPORTANT: Your output MUST be a valid JSON object with EXACTLY these fields:
- REASONING: A list of strings containing your reasoning points
- LINKS: A list of strings containing the URLs you used
- SCORE: Either "PASS" or "FAIL"

Example of valid output:
{
    "REASONING": ["reasoning point 1", "reasoning point 2"],
    "LINKS": ["https://example.com/1", "https://example.com/2"],
    "SCORE": "PASS"
}

DO NOT include any text before or after the JSON object. DO NOT use markdown formatting. The output must be parseable as valid JSON.
"""


fact_checking_from_sources_prompt_template = """Given the following DOCUMENTS and CLAIM you must analyze the claim and determine whether the answer is factually consistent with the provided sources.

    
    The CLAIM must not offer new information beyond the information provided in the DOCUMENTS.

    The CLAIM also must not contradict information provided in the DOCUMENTS.

    Output your final score by strictly following this format: "PASS" if the answer is faithful to the DOCUMENTS and "FAIL" if the answer is not faithful to the DOCUMENTS.

    Show your reasoning. Be concise in the reasoning and focus more on the failures, if any.

    Output your final score by strictly following this format: "PASS" if the claim is factual, "FAIL" if the claim is not factual.

    --
    CLAIM:
    {claim}

    DOCUMENTS:
    {documents}

    --

    Your output should be in JSON FORMAT with the keys "REASONING" and "SCORE".

    Ensure that the JSON is valid and properly formatted as follows:

    {{"REASONING": ["<your reasoning as bullet points>"], "SCORE": "<PASS or FAIL>"}}

    """


answer_decomposition_prompt_template = """
    Given the following question and answer, extract individual claims or statements from the answer.
    Each claim should be a self-contained statement that will subsequently be checked for faithfulness and factuality.

    [Example 1]
    Question: What is the capital of France?
    Answer: The capital of France is Paris. It has a population of 2.1 million people.
    Claims: ["The capital of France is Paris.", "Paris has a population of 2.1 million people."]

    [Example 2]
    Question: What is the capital of France?
    Answer: It is Paris where the Eiffel Tower is located.
    Claims: ["The capital of France is Paris.", "The Eiffel Tower is in Paris."]

    Return your answer as a JSON array of strings, each representing a single claim.
    QUESTION:
    {question}

    ANSWER:
    {answer}
        """


hallucination_detection_factchecking_workflow_template = """Given the following QUESTION, DOCUMENT and ANSWER.

    
    Do the following:

    1. Break the answer down into seperate claims (or statements).
    2. Assess if each claim is checkworthy. A checkworthy claim is one that can be verified from information sources. For example, if a claim is an opinion or an expression, it cannot be checked for verified.
    3. Assess if the question can be answered using information in the context.
    4. If the question can be answered by the document, do a hallucination check using the context.
    5. If the question cannot be answered by the document, do a factuality check using external sources like web information or internal knowledge bases.
    6. If the question can be answered by the document, but the claim is not faithfull to the context, do a factuality check using external sources like web information or internal knowledge bases.

    --------------------------------------------------------------------------------------------------------------------------
    To do a hallucination check:

    1. Check the claim against the document to determine if its faithful to the document.
    2. Output your final score by strictly following this format: "PASS" if the claim is faithful, "FAIL" if the claim is not faithful, and "NA" if the claim is not checkworthy.
    3. Show your reasoning for your assessments.

    ---------------------------------------------------------------------------------------------------------------------------
    To do a factuality check:

    1. Do a web search, or a search on internal knowledge bases (if applicable) to find information related to the claims and use the content for fact-checking.
    2. Prioritise established sources of truth like Wikipedia and established news sites for factuality checks.
    3. Provide URLs to the sources for factchecking and show the snippets used to support the claims.
    4. Output your final score by strictly following this format: "PASS" if the claim is factual, "FAIL" if the claim is not factual, and "NA" if the claim is not checkworthy.
    5. Show your reasoning for your assessments.

    -----------------------------------------------------------------------------------------------------------------------------------------
    OUTPUT FORMAT:

    For each question answer pair, output a JSON dictionary with the following keys:
    - question: The question to the response being assessed
    - answer: The answer being assessed
    - answerable_by_context: Whether the question is answerable by the context
    - claims_check: A list of the decomposed claims from the answer, each with the following fields:
        - claim: The decomposed claim
        - checkworthy_reasoning: Reasoning for whether the claim is checkworthy
        - checkworthy: Assesment on whether the claim is checkworthy. IMPORTANT: If the claim is not checkworthy, the value for the subsequent fields will be "NA"
        - check_type: "hallucination" if question is answerable by context, "factuality" if the question is not answerable by context, or if the claim is answerable by the context but the claim is not faithful to the context.
        - final_score_reasoning: Reasoning for your final score in bullet points. IMPORTANT: this is the reasoning for the assessment of whether the claim is hallucinated or factual. It is not the assessment for check-worthiness. 
        - score: PASS or FAIL according to the checks applied


    EXAMPLE OUTPUT FORMAT:
    {{
        "question": question,
        "answer": answer,
        "answerable_by_context": <PASS or FAIL>,
        "claims_check": [            
                {{"claim": claim_1, "checkworthy_reasoning": <reason for whether claim is checkworthy>, "checkworthy": <PASS OR FAIL>, "check_type":" <type of check applied>, "reasoning": ["<reasoning as bullet points for assessment>"], "score": "<PASS OR FAIL>"]}},
                {{"claim": claim_2, "checkworthy_reasoning": <reason for whether claim is checkworthy>, "checkworthy": <PASS OR FAIL>, "check_type":" <type of check applied>, "reasoning": ["<reasoning as bullet points for assessment>"], "score": "<PASS OR FAIL>"]}},
                {{"claim": claim_3, "checkworthy_reasoning": <reason for whether claim is checkworthy>, "checkworthy": <PASS OR FAIL>, "check_type":" <type of check applied>, "reasoning": ["<reasoning as bullet points for assessment>"], "score": "<PASS OR FAIL>"]}},                
        ]
    }}
    

    ==================================================================================================================================================
    These is the information given to you.

    --
    QUESTION (THIS DOES NOT COUNT AS BACKGROUND INFORMATION):
    {question}

    --
    DOCUMENT:
    {context}

    --
    ANSWER:
    {answer}

    --
    """