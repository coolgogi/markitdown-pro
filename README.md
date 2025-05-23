# MarkItDown-Pro

**MarkItDown-Pro** is an **improvement** of the **[Microsoft MarkItDown repository](https://github.com/markitdown)**, enhancing gaps and extending functionality by leveraging **Azure Document Intelligence SDK**, **Unstructured.io**, and other Azure services and libraries. The result is a comprehensive Python library and command-line tool designed to **convert diverse document formats into Markdown** with graceful fallbacks, including OCR support via GPT-4o-mini.

---

## Table of Contents

- [Folder Structure](#folder-structure)
- [Features & Highlights](#features--highlights)
- [How It Works](#how-it-works)
- [File-by-File Explanation](#file-by-file-explanation)
  - [Main Files](#main-files)
  - [Common Utils](#common-utils)
  - [Converters](#converters)
  - [Handlers](#handlers)
- [Testing](#testing)
- [Usage & Examples](#usage--examples)
  - [CLI Usage](#cli-usage)
  - [Programmatic Usage](#programmatic-usage)
  - [Extra: Vector Database Chunking](#extra-vector-database-chunking)
- [Environment Variables](#environment-variables)
- [FAQ](#faq)

---

## Folder Structure

A typical layout for **MarkItDown-Pro** might look like this:
```bash
markitdown-pro/
├── .env
├── README.md
├── requirements.txt
├── main.py
├── conversion_pipeline.py
├── common
│   └── utils.py
├── converters
│   ├── markitdown_wrapper.py
│   ├── azure_docint.py
│   ├── unstructured_wrapper.py
│   └── gpt4o_mini_vision.py
├── handlers
│   ├── pst_handler.py
│   ├── email_handler.py
│   ├── zip_handler.py
│   ├── audio_handler.py
│   └── pdf_handler.py
└──  tests
    ├── data
    └── test.py
```

| Folder/File                 | Description                                                                           |
|----------------------------|---------------------------------------------------------------------------------------|
| **main.py**                | Entry point for CLI usage; uses `argparse` to accept file paths.                      |
| **conversion_pipeline.py** | Orchestrates the fallback chain for converting documents to Markdown.                |
| **common/**                | Shared utility functions, e.g. for file detection, text cleanup, etc.                 |
| **converters/**            | Contains modules for using various 3rd-party libraries or services to extract text.   |
| **handlers/**              | Specialized handlers for specific file types (PST, EML, ZIP, audio, PDF scanning).    |
| **.env**                   | Environment variables (e.g., credentials for Azure GPT-4o-mini, Azure Doc Intelligence). |
| **requirements.txt**       | Python dependencies needed to install and run this project.                           |
| **tests/test_markitdownpro.py**| Recursively scans /tests/data/ and attempts to convert each file using convert_document_to_md|
| **README.md**              | This documentation file, explaining usage and details of the project.                 |

---

## Features & Highlights

1. **MarkItDown with LLM**
   - Uses **MarkItDown** to convert documents to Markdown, optionally leveraging an OpenAI LLM to create image captions if you have an **OPENAI_API_KEY**.
   - Auto-checks for `exiftool` if you want EXIF metadata in your images.

2. **Whisper-Based Audio Transcription**
   - Converts audio files (`.mp3`, `.wav`, `.ogg`, etc.) into text using [OpenAI Whisper](https://github.com/openai/whisper).
   - Gracefully falls back if Whisper is not installed.

3. **PST Extraction**
   - Parses Outlook PST files with [`libratom`](https://github.com/rafproject/libratom), extracting emails and attachments recursively.

4. **Scanned PDF Detection & Concurrency**
   - Identifies PDFs with no text or embedded images, and automatically performs OCR on each page with GPT-4o-mini.
   - Offers concurrent page-by-page OCR for faster performance.

5. **Fallback to Azure Document Intelligence & Unstructured**
   - If standard MarkItDown or specialized handlers fail or yield insufficient text, it tries Azure’s Document Intelligence to extract textual layout.
   - Unstructured.io library for broad coverage of file types.

6. **GPT-4 Vision (or GPT-4o-mini) for Images & OCR**
   - If an image or partially scanned PDF is detected, we can pass it to GPT-4o-mini for OCR.
   - Supports local images (base64 encoding) or remote image URLs directly.

7. **Handles ZIP & EML**
   - **ZIP**: Unzips and processes each file inside, concatenating the results.
   - **EML**: Extracts email text, attachments, and processes attachments recursively.

8. **Graceful LLM Handling**
   - If no **OPENAI_API_KEY** or GPT-4o-mini credentials are provided, it simply skips LLM-based features, logging a warning.

9. **Helper Methods for URL & Stream Conversion**
   - `convert_document_from_url(url, output_md)`
   - `convert_document_from_stream(stream, extension, output_md)`
   - `convert_document_to_md(local_path, output_md)`

10. **Easy-to-Extend Architecture**
   Each file type has its own **handler**. Each text-extraction library has its own **converter**. The main pipeline provides a centralized fallback sequence.

11. **Environment-Driven Configuration**
   - Pulls API keys, endpoints, and paths from `.env` to keep secrets out of source code.

12. **Rich File Type Handling**

| Category              | File Type(s) |
|-----------------------|-------------|
| PDF                  | .pdf |
| PowerPoint           | .pot, .potm, .ppt, .pptm, .pptx |
| Word Processing      | .abw, .doc, .docm, .docx, .dot, .dotm, .hwp, .zabw |
| Excel/Spreadsheet    | .et, .fods, .uos1, .uos2, .wk2, .xls, .xlsb, .xlsm, .xlsx, .xlw |
| Images              | .bmp, .gif, .heic, .jpeg, .jpg, .png, .prn, .svg, .tiff, .webp |
| Audio               | .mp3, .wav, .ogg, .flac, .m4a, .aac, .wma, .webm, .opus |
| HTML                | .htm, .html |
| Text-Based Formats  | .csv, .json, .xml, .txt |
| ZIP Files           | (Iterates over contents) |
| Email               | .eml, .p7s |
| PST                 | .pst |
| EPUB                | .epub |
| Markdown            | .md |
| Org Mode            | .org |
| Open Office         | .odt, .sgl |
| Other              | .eth, .mw, .pbd, .sdp, .uof, .web |
| Plain Text          | .txt |
| reStructured Text   | .rst |
| Rich Text           | .rtf |
| StarOffice          | .sxg |
| TSV                 | .tsv |
| Apple               | .cwk, .mcw, .pages |
| Data Interchange    | .dif |
| dBase               | .dbf |
| Microsoft Office    | .docx, .xlsx, .pptx |
| HEIF Image Format   | .heif |


---

## How It Works

1. **Detect File Type**: The pipeline checks the file extension or general signature (`.pdf`, `.zip`, `.eml`, `.docx`, `.mp3`, etc.).
2. **Specialized Handlers**: If the file is PST, EML, ZIP, or audio, it’s handed off to a dedicated module that handles that format.
3. **MarkItDown**: For most generic document conversions, we first try [MarkItDown](https://github.com/markitdown).
4. **Unstructured**: If MarkItDown fails or yields minimal text, we turn to [Unstructured.io](https://unstructured.io/) next.
   - **Why?** It's typically **cheaper** than Azure Document Intelligence, and can handle partial OCR scenarios (via Tesseract, PaddleOCR, etc., if you configure `OCR_AGENT`).
5. **Azure Document Intelligence**: If Unstructured also fails or yields minimal text, we try Azure Document Intelligence (prebuilt-layout).
6. **GPT-4o-mini**: As a final fallback or specifically for OCR on images/scanned pages.
7. **Saves** the extracted text to a `.md` file once any method returns sufficient content.

---

## File-by-File Explanation

### Main Files

- **`conversion_pipeline.py`**
  The core logic that orchestrates the fallback chain. Checks each handler or converter in a specific order. Once a successful conversion with enough text is found, it writes to `.md` and stops.

### Common Utils

- **`common/utils.py`**
  - **File Detection**: Contains helper functions like `is_pdf`, `is_audio`, `detect_extension`.
  - **Markdown Cleaning**: Functions like `clean_markdown()` and `ensure_minimum_content()` to tidy up text and ensure it’s not empty.

### Converters

- **`converters/markitdown_wrapper.py`**
  - Wraps the [MarkItDown](https://github.com/markitdown) library for docx/image extraction, EXIF reading, and optional LLM-based image captioning.
  - If MarkItDown is not installed, or fails, returns `None`.

- **`converters/azure_docint.py`**
  - Leverages Azure’s Document Intelligence (prebuilt-layout) to extract text from PDFs and other document types in Markdown format.

- **`converters/unstructured_wrapper.py`**
  - Uses the [Unstructured.io](https://www.unstructured.io/) library to parse documents. Useful for handling broad, less-common file types.

- **`converters/gpt4o_mini_vision.py`**
  - Uses GPT-4o-mini (Azure ChatOpenAI) for OCR tasks on **images** or **scanned PDFs**.
  - **Concurrent** or **simple** page-by-page approaches for PDFs.
  - Can pass **URL-based images** or **local images** via Base64 encoding.

### Handlers

- **`handlers/pst_handler.py`**
  - Parses PST archives with [`libratom`](https://github.com/rafproject/libratom) and extracts emails + attachments. Calls back into the pipeline for each attachment.

- **`handlers/email_handler.py`**
  - Processes `.eml` files, extracting plain text, attachments, etc. Recursively processes attachments.

- **`handlers/zip_handler.py`**
  - Unzips files, recurses into the pipeline for each contained file, and concatenates all Markdown output.

- **`handlers/audio_handler.py`**
  - Uses [OpenAI Whisper](https://github.com/openai/whisper) to transcribe `.mp3`, `.wav`, `.ogg`, etc.
  - Caches the model in memory to speed up repeated use.

- **`handlers/pdf_handler.py`**
  - Utility to detect if a PDF is text-only, text+images, or fully scanned.
  - Coordinates with GPT-4o-mini for OCR if needed.

---

## Installation

1. **Clone the Repo**
   ```bash
   git clone https://github.com/YourName/markitdown-pro.git
   cd markitdown-pro
   ```
2. **Create a Virtual Environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```
3. **Create a Virtual Environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```
4. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
  Note: You may also need system dependencies for libraries like PyMuPDF, libratom, etc.

5. **Set Up .env**

- Copy the sample .env to your root folder, and fill in your Azure or OpenAI API keys, etc. For example:
   ```bash
   AZURE_DOCINTEL_ENDPOINT="https://<your-region>.api.cognitive.microsoft.com"
   AZURE_DOCINTEL_KEY="YOUR_AZURE_KEY"
   GPT4oMINI_DEPLOYMENT_NAME="your-azure-gpt4o-mini-deployment"
   OPENAI_API_KEY="sk-...."  # needed if you want LLM-based image captioning in MarkItDown
   EXIFTOOL_PATH="/usr/local/bin/exiftool"  # optional if exiftool is not in PATH
   OCR_AGENT="unstructured.partition.utils.ocr_models.tesseract_ocr.OCRAgentTesseract" # or another supported agent for built-in OCR in Unstructured. S
   ```
  Make sure to source it or ensure python-dotenv can read it.
---

## Testing

We use **pytest** for running our test suite. The test files and scripts are located in the `/tests` directory:
   ```bash
   pytest tests/test_markitdownpro.py
   ```

---

## Usage
### CLI Usage
1. **Basic:**
   ```bash
   python main.py /path/to/document.pdf
   ```
   This will produce /path/to/document.md if successful.

2. **Specify Output Path:**
   ```bash
   python main.py /path/to/document.pst --output my_pst_output.md
   ```
### Programmatic Usage
You can import and call the pipeline directly from your Python code:
   ```python
   from conversion_pipeline import convert_document_to_md, convert_document_from_url

# 1) Local file example
md_text = convert_document_to_md("/path/to/my_file.pdf")
print("Extracted Markdown:", md_text)

# 2) URL example
md_from_url = convert_document_from_url("https://example.com/my_doc.docx", output_md="output_doc.md")
print("Output saved to output_doc.md")
```
---

## Extra: Vector Database Chunking
After converting a document to Markdown, it’s common to chunk the text before sending it to a vector database. Here’s a minimal example using LangChain:

```python
from langchain.text_splitter import MarkdownTextSplitter

# Load your Markdown content
with open('your_markdown_file.md', 'r') as file:
    markdown_text = file.read()

# Initialize the MarkdownTextSplitter
markdown_splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=100)

# Split the text into chunks
chunks = markdown_splitter.create_documents([markdown_text])

# Each chunk is now ready for embedding and ingestion into your vector database
for chunk in chunks:
    # e.g., push chunk.text to your VectorDB
    pass
```

---
## FAQ
1. **What if MarkItDown or Whisper is not installed?**
  The pipeline checks for each library’s availability. If a library is missing or fails, it gracefully moves on to the next fallback.

2. **Do I need Azure/OpenAI credentials?**

  Azure: If you want to use Document Intelligence or GPT-4o-mini, yes.
  OpenAI: If you want MarkItDown’s LLM-based image captioning or are using Whisper from openai’s library, you need appropriate credentials or local models.
  How do I handle large PST files?
  Large PSTs can be slow to process, especially if they contain many attachments. We parse them message-by-message, recursively handling attachments. For extremely large archives, you might want to increase concurrency or filter out attachments you don’t need.

3. **Does GPT-4o-mini require a publicly accessible image URL?**

  If you provide a local file path, the code base64-encodes it. This is ideal for truly local images.
  If you have a publicly hosted image, you can pass its URL directly.

4. **Why is Unstructured tried before Azure Doc Intelligence now?**
  We observed that **Unstructured** is typically **lower cost** to run (especially with Tesseract or local OCR) compared to Azure’s \$10 per 1,000 pages. So if MarkItDown fails, we want to try Unstructured next to potentially save cost. If that also fails, we move to Azure.

