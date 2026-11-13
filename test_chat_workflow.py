import asyncio

import axxonParser
import input_handler
import pymupdf
import reranker
from chat_history import ChatHistory
from matcher import rank_pages


def test_flags_route_calculations_and_ignore_other_flags(monkeypatch):
    handler = input_handler.InputHandler()
    calls = []

    async def calculation(message, save=False):
        calls.append(("calculation", message, save))
        return "calculated"

    async def conversation(message, chat_id):
        calls.append(("conversation", message, chat_id))
        return "answered"

    monkeypatch.setattr(handler, "handle_calculation", calculation)
    monkeypatch.setattr(handler, "handle_conversation", conversation)

    assert asyncio.run(
        handler.handle_input(".calc .save camera sayısı 20", chat_id=1)
    ) == "calculated"
    assert asyncio.run(
        handler.handle_input(".unknown .doc arşiv süresi nedir", chat_id=2)
    ) == "answered"
    assert calls == [
        ("calculation", "camera sayısı 20", True),
        ("conversation", "arşiv süresi nedir", 2),
    ]


def test_keyword_search_ranks_matching_page():
    pages = [
        {"page_number": 1, "content": "Kamera çözünürlüğü ve fps ayarları."},
        {"page_number": 2, "content": "Kamera arşiv saklama süresi ve disk hesabı."},
        {"page_number": 3, "content": "Kullanıcı hesap ayarları."},
    ]

    assert rank_pages("kamera arşiv süresi", pages, n=2)[0] == 2


def test_candidate_retrieval_merges_embedding_and_keyword_matches(monkeypatch):
    handler = input_handler.InputHandler()
    pages = [
        {"page_number": 1, "content": "Kamera çözünürlüğü."},
        {"page_number": 2, "content": "Arşiv disk hesabı."},
    ]
    monkeypatch.setattr(input_handler.axxonParser, "get_pages", lambda path: pages)
    monkeypatch.setattr(input_handler.embedding, "query", lambda query, n: [2])
    monkeypatch.setattr(input_handler, "rank_pages", lambda query, docs, n: [1, 2])

    candidates = handler._retrieve_candidates("kamera arşiv")

    assert candidates == [pages[1], pages[0]]


def test_pdf_page_numbers_are_one_based(tmp_path):
    pdf_path = tmp_path / "pages.pdf"
    document = pymupdf.open()
    document.new_page()
    document.new_page()
    document.save(pdf_path)
    document.close()

    assert [
        page["page_number"]
        for page in axxonParser.get_pages(str(pdf_path))
    ] == [1, 2]


def test_conversation_uses_only_high_confidence_reranked_pages(monkeypatch):
    handler = input_handler.InputHandler()
    candidates = [
        {"page_number": 7, "content": "İlgili kaynak içeriği"},
        {"page_number": 8, "content": "Düşük alakalı içerik"},
    ]
    monkeypatch.setattr(handler, "_retrieve_candidates", lambda query: candidates)

    async def fake_rerank(query, pages):
        return [
            {**pages[0], "relevance": 91},
            {**pages[1], "relevance": 84},
        ]

    captured = {}

    async def fake_llm(query, system_prompt=None):
        captured["query"] = query
        captured["system_prompt"] = system_prompt
        return "Yanıt"

    monkeypatch.setattr(input_handler.reranker, "rerank", fake_rerank)
    monkeypatch.setattr(input_handler.llm_manager, "ask_direct_llm_async", fake_llm)
    ChatHistory.h = {9: ["önceki mesaj", "güncel soru"]}

    assert asyncio.run(handler.handle_conversation("güncel soru", 9)) == "Yanıt"
    assert captured["query"] == "güncel soru"
    assert "[Sayfa 7]" in captured["system_prompt"]
    assert "İlgili kaynak içeriği" in captured["system_prompt"]
    assert "[Sayfa 8]" not in captured["system_prompt"]
    assert "güncel soru" not in captured["system_prompt"].split(
        "Önceki sohbet mesajları:", 1
    )[1].split("Kaynak aramasından", 1)[0]


def test_reranker_discards_unknown_pages_and_invalid_scores():
    candidates = [
        {"page_number": 7, "content": "Known page"},
    ]

    ranked = reranker._parse_results(
        '{"results":['
        '{"page_number":7,"relevance":91},'
        '{"page_number":999,"relevance":100},'
        '{"page_number":7,"relevance":101}'
        ']}',
        candidates,
    )

    assert ranked == [
        {"page_number": 7, "content": "Known page", "relevance": 91.0}
    ]
