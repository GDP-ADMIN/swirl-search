'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''
import os
from typing import Any

from swirl.processors.processor import *

from gllm_privacy.pii_detector import TextAnalyzer
from gllm_privacy.pii_detector.recognizer import GDPLabsNerApiRemoteRecognizer
from swirl.anonymizer.component.pii_manager import (
    PIIManager
)

#############################################
#############################################

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

NER_API_URL = os.getenv("NER_API_URL", "")
NLP_CONFIGURATION: dict[str, Any] = {
    "nlp_engine_name": "spacy",
    "models": [
        {"lang_code": "en", "model_name": "en_core_web_lg"},
        {"lang_code": "id", "model_name": "en_core_web_sm"},
    ],
}


class AnonymizerProcessor(ResultProcessor):

    type = "AnonymizerProcessor"

    def __init__(
        self,
        results,
        provider,
        query_string,
        request_id='',
        **kwargs
    ):
        """Constructor

        Args:
            results (list): List of results from the previous processor.
            provider (object): Provider object.
            query_string (str): Query string.
            request_id (str): Request ID.
        """
        remote_recognizer_en = GDPLabsNerApiRemoteRecognizer(
            api_url=NER_API_URL,
            supported_language="en",
            api_timeout=90
        )
        remote_recognizer_id = GDPLabsNerApiRemoteRecognizer(
            api_url=NER_API_URL,
            supported_language="id",
            api_timeout=90
        )
        text_analyzer = TextAnalyzer(
            additional_recognizers=[
                remote_recognizer_en,
                remote_recognizer_id
            ],
            nlp_configuration=NLP_CONFIGURATION
        )
        # remove spaCy recognizer.
        # we use NerApiRemoteRecognizer that use Flair instead
        text_analyzer._registry.remove_recognizer("SpacyRecognizer")
        self.pii_manager = PIIManager(text_analyzer=text_analyzer)
        super().__init__(
            results,
            provider,
            query_string,
            request_id=request_id,
            **kwargs
        )

    def process(self):
        """Process the results

        Returns:
            int: Number of results modified.
        """
        pii_result = self.pii_manager.anonymize(
            text_or_chunks=self.results
        )
        self.results = pii_result.get(PIIManager.ANONYMIZED_TEXT_KEY, [])
        self.provider.anonymized_mappings = pii_result[PIIManager.ANONYMIZED_MAPPINGS_KEY]
        self.processed_results = self.results
        self.modified = len(self.processed_results)
        return self.modified


class DeanonymizerProcessor(ResultProcessor):

    type = "DeanonymizerProcessor"

    def __init__(
        self,
        results,
        provider,
        query_string,
        request_id='',
        **kwargs
    ):
        """Constructor

        Args:
            results (list): List of results from the previous processor.
            provider (object): Provider object.
            query_string (str): Query string.
            request_id (str): Request ID.
        """
        remote_recognizer_en = GDPLabsNerApiRemoteRecognizer(
            api_url=NER_API_URL,
            supported_language="en",
            api_timeout=90
        )
        remote_recognizer_id = GDPLabsNerApiRemoteRecognizer(
            api_url=NER_API_URL,
            supported_language="id",
            api_timeout=90
        )
        text_analyzer = TextAnalyzer(
            additional_recognizers=[
                remote_recognizer_en,
                remote_recognizer_id
            ],
            nlp_configuration=NLP_CONFIGURATION
        )
        # remove spaCy recognizer.
        # we use NerApiRemoteRecognizer that use Flair instead
        text_analyzer._registry.remove_recognizer("SpacyRecognizer")
        self.pii_manager = PIIManager(text_analyzer=text_analyzer)
        super().__init__(
            results,
            provider,
            query_string,
            request_id=request_id,
            **kwargs
        )

    def process(self):
        """Process the results

        Returns:
            int: Number of results modified.
        """
        deanonymize_results = self.pii_manager.deanonymize(
            text_or_chunks=self.results,
            deanonymizer_mappings=getattr(self.provider, 'anonymized_mappings', {})
        )
        self.results = deanonymize_results if deanonymize_results is not None else []
        self.processed_results = self.results
        self.modified = len(self.processed_results)
        return self.modified
