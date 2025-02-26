"""This module contains PII anonymizer component.

Authors:
    Berty C L Tobing (berty.c.l.tobing@gdplabs.id)

References:
    None
"""
import copy
from typing import Any, Optional

from gllm_core.schema import Component
from gllm_privacy.pii_detector import TextAnalyzer
from gllm_privacy.pii_detector.anonymizer import Operation
from gllm_privacy.pii_detector.constants import Entities
from gllm_privacy.pii_detector.text_anonymizer import TextAnonymizer
from langdetect import LangDetectException, detect
from gllm_privacy.pii_detector.utils.deanonymizer_mapping import (
    DeanonymizerMapping
)

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


class PIIManager(Component):
    """Class responsible for anonymizing Personally Identifiable Information (PII) in text.

    Attributes:
        ENTITIES (list): List of PII entity types to be anonymized.
        ANONYMIZED_TEXT_KEY (str): The key for the anonymized text output.
        ANONYMIZED_MAPPINGS_KEY (str): The key for the anonymized mappings output.
        TEXT_KEY (str): The key for the text input.
        OPERATION_KEY (str): The key for the operation input.
        CHUNK_DELIMITER (str): The delimiter for separating chunks.
        TITLE_BODY_DELIMITER (str): The delimiter for separating title and
            body in a chunk.
        DEANONYMIZED_MAPPINGS (str): The key for the deanonymizer mappings input.
    """

    ENTITIES = [
        Entities.BANK_ACCOUNT,
        Entities.EMAIL_ADDRESS,
        Entities.EMPLOYEE_ID,
        Entities.FACEBOOK_ACCOUNT,
        Entities.FAMILY_CARD_NUMBER,
        Entities.KTP,
        Entities.LINKEDIN_ACCOUNT,
        Entities.NPWP,
        Entities.ORGANIZATION_NAME,
        Entities.PERSON,
        Entities.PHONE_NUMBER,
        Entities.PROJECT,
    ]

    ANONYMIZED_TEXT_KEY = "anonymized_text"
    ANONYMIZED_MAPPINGS_KEY = "anonymized_mappings"
    TEXT_KEY = "text"
    OPERATION_KEY = "operation"
    CHUNK_DELIMITER = "\n---\n"
    TITLE_BODY_DELIMITER = " ||| "
    DEANONYMIZED_MAPPINGS = "deanonymizer_mapping"

    def __init__(self, text_analyzer: TextAnalyzer):
        """Initialize the PIIManager class.

        Args:
            text_analyzer (TextAnalyzer): The text analyzer.
        """
        self.text_analyzer = text_analyzer

    async def _run(self, **kwargs: Any) -> Any:
        """Run the chat history manager component.

        Args:
            kwargs (Any): The keyword arguments, which may contain the operation.

        Returns:
            Any: The result of the operation.
        """
        operation = kwargs.get(self.OPERATION_KEY, Operation.ANONYMIZE)

        if operation == Operation.ANONYMIZE:
            return self.anonymize(
                kwargs.get(self.TEXT_KEY),
            )

        if operation == Operation.DEANONYMIZE:
            return self.deanonymize(
                kwargs.get(self.TEXT_KEY),
                kwargs.get(self.DEANONYMIZED_MAPPINGS),
            )

    def anonymize(
        self,
        text_or_chunks: str | list,
    ) -> list:
        """Anonymize the provided text or chunks

        Args:
            text_or_chunks (str | list): The text or chunks to be anonymized.

        Returns:
            list: The anonymized text or chunks and the anonymized mappings.
        """
        anonymizer = TextAnonymizer(
            text_analyzer=self.text_analyzer
        )
        anonymized_text = None
        if isinstance(text_or_chunks, str):
            anonymized_text = self._anonymize_text(
                anonymizer,
                text_or_chunks
            )
        elif isinstance(text_or_chunks, list):
            anonymized_text = self._anonymize_chunks(
                anonymizer,
                text_or_chunks
            )
        else:
            logger.error("text_or_chunks must be either a string or a list")

        return {
            self.ANONYMIZED_TEXT_KEY: anonymized_text,
            self.ANONYMIZED_MAPPINGS_KEY: anonymizer.deanonymizer_mapping,
        }

    def deanonymize(
        self,
        text_or_chunks: str | list,
        deanonymizer_mappings: Optional[Any],
    ) -> Any:
        """Deanonymize the provided text or chunks.

        Args:
            text_or_chunks (str | list): The text or chunks to be deanonymized.
            deanonymizer_mappings (Optional[Any]): The deanonymizer mappings.

        Returns:
            Any: The deanonymized text or chunks.
        """
        anonymizer = TextAnonymizer(
            text_analyzer=self.text_analyzer
        )

        deanonymized_text = None
        if isinstance(text_or_chunks, str):
            deanonymized_text = self._deanonymize_text(
                anonymizer,
                text_or_chunks,
                deanonymizer_mapping=DeanonymizerMapping(
                    copy.deepcopy(deanonymizer_mappings)
                )
            )
        elif isinstance(text_or_chunks, list):
            deanonymized_text = self._deanonymize_chunks(
                anonymizer,
                text_or_chunks,
                deanonymizer_mapping=DeanonymizerMapping(
                    copy.deepcopy(deanonymizer_mappings)
                )
            )
        else:
            logger.error("text_or_chunks must be either a string or a list")

        return deanonymized_text

    def _detect_language(self, text: str) -> str:
        """Detect the language of the provided text.

        Args:
            text (str): The text to detect the language of.

        Returns:
            str: The detected language of the text. We currently only support English and Indonesian.
                If the detected language is not English we will return "id".
        """
        default_language = "id"
        try:
            language = detect(text)
        except LangDetectException:
            language = default_language
        except Exception:
            language = default_language

        language = language if language == "en" else default_language
        return language

    def _anonymize_chunks(self, anonymizer: TextAnonymizer, chunks: list) -> list:
        """Anonymize the content of the provided chunks.

        Args:
            anonymizer (TextAnonymizer): The text anonymizer.
            chunks (list): The chunks to be anonymized.

        Returns:
            list: The anonymized chunks.
        """
        combined_chunks = self._combined_chunks(chunks)
        anonymized_text = self._anonymize_text(
            anonymizer,
            combined_chunks
        )
        new_chunks = self._rebuild_chunks(anonymized_text, chunks)

        return new_chunks

    def _anonymize_text(self, anonymizer: TextAnonymizer, text: str) -> str:
        """Anonymize the provided text.

        Args:
            anonymizer (TextAnonymizer): The text anonymizer.
            text (str): The text to be anonymized.

        Returns:
            str: The anonymized text.
        """
        language = self._detect_language(text)
        anonymized_text = anonymizer.anonymize(
            text=text,
            entities=self.ENTITIES,
            language=language
        )

        return anonymized_text

    def _deanonymize_chunks(
        self,
        anonymizer: TextAnonymizer,
        chunks: list,
        deanonymizer_mapping: DeanonymizerMapping
    ) -> list:
        """Deanonymize the content of the provided chunks.

        Args:
            anonymizer (TextAnonymizer): The text anonymizer.
            chunks (list): The chunks to be deanonymized.
            deanonymizer_mapping (DeanonymizerMapping): The deanonymizer mappings.

        Returns:
            list: The deanonymized chunks.
        """
        combined_chunks = self._combined_chunks(chunks)
        deanonymized_text = self._deanonymize_text(
            anonymizer,
            combined_chunks,
            deanonymizer_mapping
        )
        new_chunks = self._rebuild_chunks(deanonymized_text, chunks)

        return new_chunks

    def _deanonymize_text(
        self,
        anonymizer: TextAnonymizer,
        text: str,
        deanonymizer_mapping: DeanonymizerMapping
    ) -> str:
        """Deanonymize the provided text.

        Args:
            anonymizer (TextAnonymizer): The text anonymizer.
            text (str): The text to be deanonymized.
            deanonymizer_mapping (DeanonymizerMapping): The deanonymizer mappings.

        Returns:
            str: The deanonymized text
        """
        anonymizer = TextAnonymizer(
            text_analyzer=self.text_analyzer,
            deanonymizer_mapping=deanonymizer_mapping,
        )
        return anonymizer.deanonymize(text)

    def _combined_chunks(self, chunks: list) -> str:
        """Combine the content of the provided chunks.

        This function concatenates the title and body of each chunk into a single string.

        Args:
            chunks (list): The chunks to be combined.

        Returns:
            str: The combined content of the chunks.
        """
        return self.CHUNK_DELIMITER.join(
            f"{chunk['title']}{self.TITLE_BODY_DELIMITER}{chunk['body']}" for chunk in chunks
        )

    def _rebuild_chunks(self, text_chunks: str, original_chunks: list) -> list:
        """Reconstruct the chunks from the combined content.

        Args:
            text_chunks (str): The combined content of the chunks.
            original_chunks (list): The original chunks.

        Returns:
            list: The reconstructed chunks.
        """
        chunks = []
        text_chunks = text_chunks.split(self.CHUNK_DELIMITER)
        for original_chunk, anonymized_chunk in zip(original_chunks, text_chunks):
            title, _, body = anonymized_chunk.partition(self.TITLE_BODY_DELIMITER)

            new_chunk = original_chunk.copy()
            new_chunk["title"] = title
            new_chunk["body"] = body

            chunks.append(new_chunk)

        return chunks
