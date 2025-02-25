"""This module contains PII anonymizer component.

Authors:
    Berty C L Tobing (berty.c.l.tobing@gdplabs.id)

References:
    None
"""

from typing import Any

from gllm_core.schema import Chunk, Component
from gllm_privacy.pii_detector import TextAnalyzer
from gllm_privacy.pii_detector.anonymizer import Operation
from gllm_privacy.pii_detector.constants import Entities
from gllm_privacy.pii_detector.text_anonymizer import TextAnonymizer
from langdetect import LangDetectException, detect


class PIIManager(Component):
    """Class responsible for anonymizing Personally Identifiable Information (PII) in text.

    Attributes:
        ENTITIES (list): List of PII entity types to be anonymized.
        TEXT_KEY (str): The key for the text input.
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

    TEXT_KEY = "text"
    OPERATION_KEY = "operation"
    CHUNK_DELIMITER = "\n---\n"

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

    def anonymize(
        self,
        text_or_chunks: str | list[Chunk],
    ) -> dict[str, Any]:
        """Anonymize the provided text or chunks

        Args:
            text_or_chunks (str | list[Chunk]): The text or list of chunks to be anonymized.

        Returns:
            dict[str, Any]: A dictionary containing the anonymized text or chunks and a list of new anonymizer mappings.
        """
        anonymizer = TextAnonymizer(
            text_analyzer=self.text_analyzer
        )

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
            raise ValueError(
                "text_or_chunks must be either a string or a list of Chunk objects"
            )

        return anonymized_text

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

    def _anonymize_chunks(self, anonymizer: TextAnonymizer, chunks: list[Chunk]) -> str:
        """Anonymize the content of the provided chunks.

        This function processes a list of chunks to anonymize its content and returns concatenated
        anonymized text from the chunk's content.

        Args:
            anonymizer (TextAnonymizer): The text anonymizer.
            chunks (list[Chunk]): The list of chunks to be anonymized.

        Returns:
            str: The anonymized text.
        """
        anonymized_text = self.CHUNK_DELIMITER.join(
            self._anonymize_text(anonymizer, chunk.content) for chunk in chunks
        )

        return anonymized_text

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
