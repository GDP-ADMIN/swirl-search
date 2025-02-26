"""This module provides a processor for FAQ results.

Authors:
    Ardhian Heru Nugroho (ardhian.h.nugroho@gdplabs.id)

References:
    None
"""
import json

from datetime import datetime

from swirl.openai.openai import AI_QUERY_USE, OpenAIClient
from swirl.processors.processor import *
from swirl.processors.utils import create_result_dictionary

#############################################
#############################################

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

MODEL_3 = "gpt-3.5-turbo"
MODEL_4 = "gpt-4"

MODEL = MODEL_3


class FAQResultProcessor(ResultProcessor):

    type = "FAQResultProcessor"

    def __init__(
        self,
        results,
        provider,
        query_string,
        request_id='',
        **kwargs
    ):
        self.system_guide = (
            "You are an AI assistant that extracts frequently asked questions (FAQs) from the given document. "
            "Identify and return exactly five relevant questions in a short and clear format. "
            "The output must be a valid JSON array containing exactly five objects. "
            "Each object must have a single key named 'question' with a short and concise question as its value. "
            "All questions must be written in Indonesian. "
            "Return only the pure JSON output without any extra text, explanations, or formatting."
        )
        super().__init__(
            results,
            provider,
            query_string,
            request_id=request_id,
            **kwargs
        )

    def process(self):
        list_results = []
        try:
            client = OpenAIClient(usage=AI_QUERY_USE)
            documents = []
            for item in self.results:
                title = item.get("title", "")
                body = item.get("body", "")
                documents.append({
                    "title": title,
                    "body": body
                })
            completions = client.openai_client.chat.completions.create(
                model=client.get_model(),
                messages=[
                    {
                        "role": "system",
                        "content": self.system_guide
                    },
                    {
                        "role": "user",
                        "content": "Extract FAQs from the following documents:\n\n" +
                        json.dumps(documents, indent=2)
                    },
                ],
                temperature=0
            )
            faq_json_str = completions.choices[0].message.content.strip()
            try:
                faq_json = json.loads(faq_json_str)
            except json.JSONDecodeError:
                faq_json = []

            result_number = 1
            for result in faq_json:
                swirl_result = create_result_dictionary()
                swirl_result['searchprovider'] = self.provider.name
                swirl_result['searchprovider_rank'] = result_number
                swirl_result['date_retrieved'] = str(datetime.now())
                swirl_result['date_published'] = 'unknown'
                swirl_result['title'] = result.get("question", "")
                result_number = result_number + 1
                list_results.append(swirl_result)
        except ValueError as valErr:
            logger.error(f"err {valErr} while initilizing OpenAI client")

        self.processed_results = list_results
        self.modified = len(self.processed_results)
        return self.modified
