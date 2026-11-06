"""
Parses PDF files into a structured format. Returns a list of passages, each containing the page number and the extracted text.
A passage could be a paragraph, a sentence, or a table.
"""
import sys
import pymupdf
from logger import Logger
from typing import List, Dict
import time

import re
from logger import Logger

class TextCleaner:
    @staticmethod
    def clean_text_file(input_path: str, output_path: str):
        Logger.info(f"Starting cleanup for file: {input_path}")
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except Exception as e:
            Logger.error(f"Failed to read file {input_path}: {e}")
            return

        Logger.system("Raw file loaded successfully. Applying cleaning pipeline...")

        # Step 1: Remove trailing long dots or dot leaders (e.g., "Chapter 1 ..... 45")
        # This matches 3 or more consecutive dots, optionally followed by numbers/spaces at line ends
        cleaned = re.sub(r'\.{3,}\s*\d*', '', raw_content)

        # Step 2: Normalize all line endings to standard \n
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')

        # Step 3: Split into potential blocks based on double newlines (blank lines)
        # A blank line indicates a true paragraph break.
        raw_blocks = re.split(r'\n\s*\n', cleaned)
        
        processed_paragraphs = []
        for block in raw_blocks:
            # Inside a block, remove single newlines (unnecessary hard wraps) and collapse multiple spaces
            unwrapped_block = re.sub(r'\s*\n\s*', ' ', block)
            
            # Clean up extra spaces around punctuation or double spaces
            normalized_block = re.sub(r'\s+', ' ', unwrapped_block).strip()
            
            if normalized_block:
                processed_paragraphs.append(normalized_block)

        # Step 4: Rejoin paragraphs cleanly with double newlines
        final_text = '\n\n'.join(processed_paragraphs)

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_text)
            Logger.system(f"Cleanup complete. Saved clean text to: {output_path}")
        except Exception as e:
            Logger.error(f"Failed to write output file {output_path}: {e}")




def get_raw_text_from_pdf(pdf_path):
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        Logger.error(f"Failed to open PDF file {pdf_path}: {e}")
        return ""

    all_text = ""
    for i, _ in enumerate(doc):
        text = doc.get_page_text(i)
        all_text += text
    return all_text


def get_pages(pdf_path) -> List[Dict[str, str]]:
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        Logger.error(f"Failed to open PDF file {pdf_path}: {e}")
        return []

    pages = []
    for i, _ in enumerate(doc):
        text = doc.get_page_text(i)
        pages.append(
            {
            "page_number": str(i),
            "content": text.strip()
            }
        )

    # DEBUG
    i= 0
    f = open("logs/page_log.txt", "w", encoding="utf-8")
    for page in pages:
        i += 1 if i!=0 else 0
        if i % 10 != 0: continue
        f.write(f"Page No: {page['page_number']} content: {page['content']}\n\n")
    f.close()
    Logger.debug("Saved sample page content to logs/page_log.txt for debugging.")

    return pages


if __name__ == "__main__":
    start_time = time.perf_counter()
    Logger.system("This is a test run of PDF module.")

    pdf_path = sys.argv[1] if len(sys.argv)> 1 else None
    if not pdf_path:
        Logger.error("Please provide a PDF file path as an argument.")
        sys.exit(1)
    raw_text = get_raw_text_from_pdf(pdf_path)
    page_text = str(get_pages(pdf_path))

    f = open(f"{pdf_path}.txt", "w", encoding="utf-8")
    f.write(raw_text)
    f.close()
    
    f = open(f"{pdf_path}_pages.txt", "w", encoding="utf-8")
    f.write(page_text)
    f.close()
        
    Logger.info(f"Extracted text from {pdf_path} and saved to {pdf_path}.txt")
    Logger.info(f"Extracted text from {pdf_path} and saved to {pdf_path}_paragraphs.txt")
    Logger.info(f"Extracted text from {pdf_path} and saved to {pdf_path}_pages.txt")
    TextCleaner.clean_text_file(f"{pdf_path}.txt", f"{pdf_path}_clean.txt")
    TextCleaner.clean_text_file(f"{pdf_path}_paragraphs.txt", f"{pdf_path}_paragraphs_clean.txt")
    TextCleaner.clean_text_file(f"{pdf_path}_pages.txt", f"{pdf_path}_pages_clean.txt")
    end_time = time.perf_counter()
    Logger.perf(f"PDF module test run completed in {end_time - start_time:.3f} seconds.")