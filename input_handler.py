import asyncio
import json
import re
from pathlib import Path

import axxonParser
import embedding
import llm_manager
import platform_calculator
import reranker
from chat_history import ChatHistory
from logger import Logger
from matcher import rank_pages


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_XML_DIR = str(PROJECT_DIR / "xml_output")
SOURCE_PDF = PROJECT_DIR / "data" / "raw_manual.pdf"
RERANK_THRESHOLD = 85
SEARCH_CANDIDATE_COUNT = 10
RESULT_COUNT = 5

FLAG_PATTERN = re.compile(r"(?<!\S)\.([A-Za-z][\w-]*)")
CALCULATION_FLAGS = {"calc", "compute", "hesap", "hesapla"}
SAVE_FLAGS = {"save", "kaydet"}


class InputHandler:
    def parse_flags(self, user_input: str) -> tuple[str, set[str]]:
        flags = {match.group(1).casefold() for match in FLAG_PATTERN.finditer(user_input)}
        message = FLAG_PATTERN.sub("", user_input).strip()
        return message, flags

    async def handle_input(self, user_input: str, chat_id: int):
        Logger.msg(user_input)
        message, flags = self.parse_flags(user_input)

        if flags & CALCULATION_FLAGS:
            return await self.handle_calculation(
                message,
                save=bool(flags & SAVE_FLAGS),
            )

        return await self.handle_conversation(message, chat_id=chat_id)

    def is_calculation_request(self, user_input: str) -> bool:
        _, flags = self.parse_flags(user_input)
        return bool(flags & CALCULATION_FLAGS)

    def is_save_calculation(self, user_input: str) -> bool:
        _, flags = self.parse_flags(user_input)
        return bool(flags & SAVE_FLAGS)

    async def parse_calculation_input(self, user_input: str) -> dict | None:
        prompt = f"""Extract parameters from the following input for a calculation: {user_input}.
        Return a dictionary with keys:
        camera_count (default 10),
        archive_days (default 30),
        resolution (default 1920x1080, always use axb format for resolution. all valid options are as follows: '200x100', '320x240', '400x200', '352x288', '704x288', '640x360', '640x480', '704x480', '704x576', '720x576', '800x600', '1024x768', '1280x720', '1280x960', '1280x1024', '1600x1200', '1920x1080', '2048x1536', '3012x1152', '2560x1440', '2688x1520', '2560x1600', '2048x2048', '2560x1920', '2592x1920', '2592x1944', '2560x2048', '3072x1728', '3072x2048', '2560x2560', '3072x2304', '6400x1200', '3840x2160', '4096x2160', '3072x3072', '3648x2752', '4000x3000', '4000x3072', '5472x3648', '7680x4320', '8192x4320'),
        fps (default 25),
        codec (default H.264, allowed: H264, H265, MjPEG),
        recording_percentage=100 (default 100),
        return only the dictionary."""
        result = await llm_manager.ask_direct_llm_async(prompt, llm_name="qwen3:4b")
        try:
            Logger.debug(f"LLM output for parsing calculation input: {result}")
            start = result.find("{")
            end = result.rfind("}")
            if start < 0 or end < start:
                raise json.JSONDecodeError("No JSON object found", result, 0)
            values = json.loads(result[start:end + 1])
            if not isinstance(values, dict):
                raise json.JSONDecodeError("Expected a JSON object", result, start)
            return values
        except json.JSONDecodeError as error:
            Logger.error(f"Failed to parse LLM output as JSON: {error}")
            return None

    async def handle_calculation(self, user_input: str, save: bool = False):
        parsed_input = await self.parse_calculation_input(user_input)
        if parsed_input is None:
            Logger.error("Failed to parse calculation input.")
            return None

        platform_result = await platform_calculator.calculate_platform(
            camera_count=parsed_input.get("camera_count", 10),
            archive_days=parsed_input.get("archive_days", 30),
            resolution=parsed_input.get("resolution", "1920x1080"),
            fps=parsed_input.get("fps", 25),
            codec=parsed_input.get("codec", "H.265"),
            recording_percentage=parsed_input.get("recording_percentage", 50),
            save_xls_to=DEFAULT_XML_DIR if save else None,
        )

        return await llm_manager.ask_direct_llm_async(
            f"""User requested a calculation with the following parameters: {parsed_input}.
            The platform calculator returned: {platform_result}.
            Please provide a short Turkish summary. Start with each input and result in key -> value format, then briefly explain their correlation.""",
            llm_name="qwen3:4b",
            benchmark=False,
        )

    def _retrieve_candidates(self, query: str) -> list[dict]:
        pages = axxonParser.get_pages(str(SOURCE_PDF))
        if not pages:
            raise RuntimeError(f"No pages could be read from source PDF: {SOURCE_PDF}")

        semantic_page_numbers = embedding.query(query, n=SEARCH_CANDIDATE_COUNT)
        lexical_page_numbers = rank_pages(
            query,
            pages,
            n=SEARCH_CANDIDATE_COUNT,
        )

        pages_by_number = {int(page["page_number"]): page for page in pages}
        candidate_numbers = dict.fromkeys(
            semantic_page_numbers + lexical_page_numbers
        )
        return [
            pages_by_number[page_number]
            for page_number in candidate_numbers
            if page_number in pages_by_number
        ]

    async def handle_conversation(self, user_input: str, chat_id: int) -> str:
        if not user_input:
            raise ValueError("A message is required after removing message flags.")

        candidates = await asyncio.to_thread(self._retrieve_candidates, user_input)
        ranked_pages = await reranker.rerank(user_input, candidates)
        relevant_pages = [
            page for page in ranked_pages
            if page["relevance"] >= RERANK_THRESHOLD
        ][:RESULT_COUNT]

        previous_messages = ChatHistory.h.get(chat_id, [])
        if (
            previous_messages
            and self.parse_flags(previous_messages[-1])[0] == user_input
        ):
            previous_messages = previous_messages[:-1]
        previous_messages = previous_messages[-10:]

        source_context = "\n\n".join(
            f"[Sayfa {page['page_number']}]\n{page['content']}"
            for page in relevant_pages
        )
        if not source_context:
            source_context = (
                "Aramayla eşleşen ve %85 alaka eşiğini geçen kaynak bulunamadı."
            )

        history_context = "\n".join(previous_messages) or "Önceki mesaj yok."
        system_message = f"""Yanıtlarını Türkçe, kısa ve net ver; kullanıcıya "Patron" diye hitap et.
Önceki sohbet mesajları:
{history_context}

Kaynak aramasından bulunan sayfalar (PDF'deki fiziksel sayfa numaraları):
{source_context}

Kaynakla ilgili sorularda yalnızca verilen sayfa içeriklerini dayanak al. Bir kaynak kullanırsan sadece verilen [Sayfa N] biçimini kullan; sayfa numarası uydurma veya değiştirme. Kaynaklarda cevap yoksa bunu açıkça belirt ve kaynak gösterme."""

        return await llm_manager.ask_direct_llm_async(
            user_input,
            system_prompt=system_message,
        )
