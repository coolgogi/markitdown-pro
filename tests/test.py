from pathlib import Path
from typing import Tuple

import pytest
from dotenv import load_dotenv

from markitdown_pro.conversion_pipeline import ConversionPipeline

from .fixtures import data_path, expected_md_content

SCRIPT_DIR = Path(__file__).parent.resolve()
ENV_PATH = SCRIPT_DIR / ".test.env"

if not ENV_PATH.exists():
    raise FileNotFoundError(
        f"The .test.env file is missing in {SCRIPT_DIR!s}. "
        "Please create it with the required environment variables."
    )

# load environment variables from that file
load_dotenv(dotenv_path=str(ENV_PATH))

ALL_FILES = []
for file_extension in expected_md_content().keys():
    for file in expected_md_content()[file_extension].keys():
        ALL_FILES.append((file_extension, file, data_path() / file_extension / file))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "file_tuple",
    ALL_FILES,
    ids=[str(p.relative_to(data_path() / e)) for e, f, p in ALL_FILES],
)
async def test_files(
    file_tuple: Tuple[str, str, Path],
    pipeline: ConversionPipeline,
):
    """
    Test converting each file in the data directory to Markdown.
    """
    # Use the pipeline fixture to convert the file to Markdown.
    file_extension, file_name, file_path = file_tuple
    markdown_text = await pipeline.convert_document_to_md(str(file_path.absolute()))

    # not null validation
    assert markdown_text is not None, f"Conversion returned None for {file_path.name}"

    # type validation
    assert isinstance(markdown_text, str), f"Output type is not str for {file_path.name}"

    # Strip whitespace to ensure we're checking content, not just whitespace.
    assert markdown_text.strip() != "", f"Markdown output is empty for {file_path.name}"

    # validate content
    for expected_phrase in expected_md_content()[file_extension][file_name]:
        assert (
            expected_phrase in markdown_text
        ), f"Missing expected content '{expected_phrase}' in output for {file_path.name}"
