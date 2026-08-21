from __future__ import annotations

import os

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import (
    ContentAnalyzer,
    ContentAnalyzerConfig,
    ContentFieldDefinition,
    ContentFieldSchema,
    ContentFieldType,
    GenerationMethod,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    endpoint = os.environ["CONTENTUNDERSTANDING_ENDPOINT"].rstrip("/")
    analyzer_id = os.environ["CONTENTUNDERSTANDING_ANALYZER_ID"]
    credential = DefaultAzureCredential()
    try:
        with ContentUnderstandingClient(endpoint=endpoint, credential=credential) as client:
            client.update_defaults(
                model_deployments={
                    "gpt-5.2": "gpt-5.2",
                    "text-embedding-3-large": "text-embedding-3-large",
                    "prebuilt-analyzer-completion": "gpt-5.2",
                    "prebuilt-analyzer-completion-mini": "gpt-5.2",
                    "prebuilt-analyzer-embedding": "text-embedding-3-large",
                }
            )
            schema = ContentFieldSchema(
                name="mortgage_payslip",
                description="Fields required for a preliminary Bank Alfa mortgage assessment.",
                fields={
                    "employer_name": ContentFieldDefinition(
                        type=ContentFieldType.STRING,
                        method=GenerationMethod.EXTRACT,
                        description="Legal name of the employer issuing the payslip.",
                        estimate_source_and_confidence=True,
                    ),
                    "gross_salary_monthly": ContentFieldDefinition(
                        type=ContentFieldType.NUMBER,
                        method=GenerationMethod.EXTRACT,
                        description="Gross monthly salary in SEK, as a number without currency symbols.",
                        estimate_source_and_confidence=True,
                    ),
                    "net_salary_monthly": ContentFieldDefinition(
                        type=ContentFieldType.NUMBER,
                        method=GenerationMethod.EXTRACT,
                        description="Net monthly salary in SEK, as a number without currency symbols.",
                        estimate_source_and_confidence=True,
                    ),
                    "employment_type": ContentFieldDefinition(
                        type=ContentFieldType.STRING,
                        method=GenerationMethod.EXTRACT,
                        description="Employment type and working-time arrangement stated on the payslip.",
                        estimate_source_and_confidence=True,
                    ),
                    "pay_date": ContentFieldDefinition(
                        type=ContentFieldType.DATE,
                        method=GenerationMethod.EXTRACT,
                        description="Date on which the salary was or will be paid.",
                        estimate_source_and_confidence=True,
                    ),
                },
            )
            analyzer = ContentAnalyzer(
                base_analyzer_id="prebuilt-document",
                description="Extract verified income fields from Swedish or English payslips.",
                config=ContentAnalyzerConfig(
                    locales=["sv-SE", "en-US"],
                    enable_layout=True,
                    enable_ocr=True,
                    estimate_field_source_and_confidence=True,
                    return_details=True,
                ),
                field_schema=schema,
                models={
                    "completion": "gpt-5.2",
                    "embedding": "text-embedding-3-large",
                },
            )
            poller = client.begin_create_analyzer(
                analyzer_id=analyzer_id,
                resource=analyzer,
                allow_replace=True,
            )
            result = poller.result()
            print(f"CONTENT_UNDERSTANDING_ANALYZER_READY={result.analyzer_id}")
    finally:
        credential.close()


if __name__ == "__main__":
    main()