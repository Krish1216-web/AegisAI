# Document Extraction Services

AegisAI employs specific parser implementations for text extraction. All extractors implement the common interface `BaseDocumentExtractor`.

## 1. Supported Extractor Engines

| Format | Extractor | Backend Parser | Output Structure |
| :--- | :--- | :--- | :--- |
| **PDF** | `PDFExtractor` | `pypdf` | Pages with text content. Detects encrypted or empty PDFs. |
| **DOCX** | `DOCXExtractor` | `python-docx` | Sections mapped by headings. Retains pipe-separated table records. |
| **PPTX** | `PPTXExtractor` | `python-pptx` | Slides mapped as logical pages. Extracts text boxes and titles. |
| **XLSX** | `XLSXExtractor` | `openpyxl` | Sheets mapped by sections. Cell values pipe-separated. |
| **TXT** | `TextExtractor` | Python Native | Plaintext payload with UTF-8/fallback encoding detection. |
| **CSV** | `CSVExtractor` | Python `csv` | Table rows representing text suitable for chunking. Delimiter sniffing. |
| **Image** | `ImageExtractor` | PIL (`Pillow`) | Image metadata (width, height, format). Hooked to OCR abstraction. |
| **Audio/Video** | `AudioVideoExtractor` | wave container / Native | WAV sample metadata extraction (duration, channels, sample rate). |

## 2. Limits and Truncations
- **XLSX Limits**: Truncated above 1,000 rows or 10,000 cells per workbook.
- **CSV Limits**: Truncated above 2,000 rows.
- **OCR Fallback**: Images utilize a `MockOCRProvider` returning empty strings when no heavy external engine is registered.
