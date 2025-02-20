'''
@author:     Ardhian Heru Nugroho
@contact:    ardhian.h.nugroho@gdplabs.id
'''

from os import environ
from sys import path

import django
import json

from celery.utils.log import get_task_logger
from swirl.connectors.requestspost import RequestsPost
from swirl.openai.openai import AI_QUERY_USE, OpenAIClient
from swirl.utils import swirl_setdir

path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()
logger = get_task_logger(__name__)

MODEL_3 = "gpt-3.5-turbo"
MODEL_4 = "gpt-4"

MODEL = MODEL_3


class LLMRequestsPost(RequestsPost):

    type = "LLMRequestsPost"

    def __init__(self, provider_id, search_id, update, request_id=''):
        self.system_guide = (
            "You are an AI assistant that extracts frequently asked questions (FAQs) from the given document. "
            "Identify and return exactly five relevant questions in a short and clear format. "
            "The output must be a valid JSON array containing exactly five objects. "
            "Each object must have a single key named 'question' with a short and concise question as its value. "
            "All questions must be written in Indonesian. "
            "Return only the pure JSON output without any extra text, explanations, or formatting."
        )
        super().__init__(provider_id, search_id, update, request_id)

    def send_request(self, url, params=None, query=None, **kwargs):
        response = super().send_request(url, params, query, **kwargs)
        if response.status_code == 200:
            response_json = response.json()
            documents = []
            for hit in response_json.get("hits", {}).get("hits", []):
                text = hit.get("_source", {}).get("text", "")
                documents.append({"text": text})
            client = None
            try:
                client = OpenAIClient(usage=AI_QUERY_USE)
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
                response_json["faq"] = faq_json
                modified_text = json.dumps(response_json)
                response._content = modified_text.encode(response.encoding or 'utf-8')
            except ValueError as valErr:
                logger.error(f"err {valErr} while initilizing OpenAI client")

        return response
