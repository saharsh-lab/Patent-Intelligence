"""Phase 2 (no database): file validation, extraction, cleaning, sections, chunking, embeddings."""

import math
import sys
import types

import pytest

from app.core.errors import (
    ConfigurationError,
    EmptyDocumentError,
    ExternalServiceError,
    InvalidDocumentError,
    UnsupportedFileError,
)
from app.rag import embeddings as embeddings_module
from app.rag.chunking import chunk_document
from app.rag.cleaning import clean_pages
from app.rag.embeddings import FakeEmbedder, LocalEmbedder, OpenAICompatibleEmbedder
from app.rag.extraction import Page, detect_file_kind, extract_pages
from app.rag.ingestion import process_document
from app.rag.sections import match_heading, structure_document
from app.services.documents import sanitize_filename
from tests.helpers import fixture_bytes, make_docx, make_pdf

BATTERY = fixture_bytes("battery_patent.txt")


# ------------------------------------------------------------------ file validation


@pytest.mark.parametrize(
    ("filename", "data", "error"),
    [
        ("report.pdf", b"just some text pretending to be a PDF", InvalidDocumentError),
        ("report.docx", b"not a zip archive", InvalidDocumentError),
        ("notes.txt", b"text\x00with\x00binary", InvalidDocumentError),
        ("virus.exe", b"MZ\x90\x00", UnsupportedFileError),
        ("no_extension", b"hello", UnsupportedFileError),
    ],
)
def test_file_type_is_checked_by_content_not_just_name(filename, data, error):
    with pytest.raises(error):
        detect_file_kind(filename, data)


def test_zip_that_is_not_a_word_document_is_rejected():
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("hello.txt", "hi")
    with pytest.raises(InvalidDocumentError):
        detect_file_kind("fake.docx", buffer.getvalue())


def test_real_files_are_detected():
    assert detect_file_kind("a.PDF", make_pdf([["Hello world"]])) == "pdf"
    assert detect_file_kind("a.docx", make_docx(["Hello world"])) == "docx"
    assert detect_file_kind("a.txt", BATTERY) == "txt"


# ------------------------------------------------------------------ extraction


def test_pdf_without_text_suggests_ocr():
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()  # a blank page behaves like a scanned image: no text layer
    with pytest.raises(EmptyDocumentError, match="OCR"):
        extract_pages("pdf", doc.tobytes())


def test_corrupted_pdf_is_rejected():
    with pytest.raises(InvalidDocumentError):
        extract_pages("pdf", b"%PDF-1.7\n this is not really a pdf body")


def test_encrypted_pdf_is_rejected():
    import pymupdf

    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Secret patent text " * 5)
    data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="pw", owner_pw="pw")
    with pytest.raises(InvalidDocumentError, match="password"):
        extract_pages("pdf", data)


def test_pdf_page_limit():
    with pytest.raises(InvalidDocumentError, match="limit"):
        extract_pages("pdf", make_pdf([["page one text"], ["page two text"]]), max_pages=1)


def test_docx_paragraphs_and_tables_are_extracted():
    data = make_docx(
        ["ABSTRACT", "A coil transfers power wirelessly to a phone."],
        table=[["Parameter", "Value"], ["Frequency", "140 kHz"]],
    )
    blocks = extract_pages("docx", data)[0].blocks
    assert "A coil transfers power wirelessly to a phone." in blocks
    assert "Frequency | 140 kHz" in blocks


def test_txt_in_windows_encoding_is_read():
    pages = extract_pages("txt", "Résumé of the café invention, with enough text.".encode("cp1252"))
    assert "café" in pages[0].blocks[0]


def test_empty_text_is_rejected():
    with pytest.raises(EmptyDocumentError):
        extract_pages("txt", b"   \n\n  ")


# ------------------------------------------------------------------ cleaning


def test_running_headers_and_page_numbers_are_removed():
    bodies = ["The pump circulates coolant.", "Each cell has a sensor.", "A fan cools air.", "End."]
    pages = [
        Page(n, [f"U.S. Patent Sheet {n} of 4 US 10,123,456 B2", body, str(n)])
        for n, body in enumerate(bodies, start=1)
    ]
    cleaned = clean_pages(pages)
    assert [p.blocks for p in cleaned] == [[body] for body in bodies]


def test_hyphenated_line_breaks_and_ligatures_are_repaired():
    cleaned = clean_pages([Page(1, ["The coil trans-\nfers power to the ﬁrst\ndevice."])])
    assert cleaned[0].blocks == ["The coil transfers power to the first device."]


def test_headings_and_claims_are_separated_from_text():
    cleaned = clean_pages([Page(None, ["CLAIMS\n1. A device.\n2. The device of claim 1."])])
    assert cleaned[0].blocks == ["CLAIMS", "1. A device.", "2. The device of claim 1."]


# ------------------------------------------------------------------ sections


@pytest.mark.parametrize(
    ("line", "section"),
    [
        ("ABSTRACT", "abstract"),
        ("(57) Abstract", "abstract"),
        ("BACKGROUND OF THE INVENTION", "background"),
        ("Description of the Related Art", "background"),
        ("SUMMARY", "summary"),
        ("BRIEF DESCRIPTION OF THE DRAWINGS", "drawings"),
        ("DETAILED DESCRIPTION OF THE PREFERRED EMBODIMENTS", "description"),
        ("What is claimed is:", "claims"),
        ("Claims", "claims"),
        ("II. TECHNICAL FIELD", "technical_field"),
        ("The abstract idea of a coil is described below.", None),
        ("1. A system comprising a sensor.", None),
    ],
)
def test_heading_detection(line, section):
    assert match_heading(line) == section


def test_all_patent_sections_found_in_sample():
    result = process_document("battery.txt", BATTERY)
    assert result.structured.section_detection == "headings"
    assert result.structured.sections_found == [
        "title",
        "abstract",
        "technical_field",
        "background",
        "summary",
        "drawings",
        "description",
        "claims",
    ]
    assert result.structured.title.startswith("Battery Thermal Management System")


def test_document_without_headings_falls_back_gracefully():
    text = b"A plain memo about coolant pumps.\n\nIt has two paragraphs and no patent headings."
    result = process_document("memo.txt", text)
    assert result.structured.section_detection == "none"
    assert all(chunk.section is None for chunk in result.chunks)


def test_patent_number_found_in_running_header():
    pdf = make_pdf(
        [["ABSTRACT", f"Text on page {n} about inductive charging coils."] for n in range(1, 4)],
        header="U.S. Patent Sheet {page} of 3 US 10,123,456 B2",
    )
    result = process_document("p.pdf", pdf)
    assert "US10123456B2" in result.structured.patent_numbers
    assert all("Sheet" not in chunk.text for chunk in result.chunks)


# ------------------------------------------------------------------ chunking


@pytest.mark.parametrize("strategy", ["section_aware", "fixed"])
def test_chunk_text_is_exact_slice_of_document(strategy):
    result = process_document("b.txt", BATTERY, strategy=strategy, max_tokens=80, overlap_tokens=15)
    for chunk in result.chunks:
        assert chunk.text == result.structured.text[chunk.char_start : chunk.char_end]
        assert chunk.token_count <= 80
    assert [c.index for c in result.chunks] == list(range(len(result.chunks)))


def test_each_claim_becomes_its_own_chunk():
    result = process_document("b.txt", BATTERY)
    claims = [c for c in result.chunks if c.section == "claims"]
    assert [c.meta["claim_number"] for c in claims] == [1, 2, 3, 4, 5]
    assert all(c.meta["kind"] == "claim" for c in claims)
    assert claims[1].text.startswith("2. The system of claim 1")


def test_chunks_never_mix_sections():
    result = process_document("b.txt", BATTERY, max_tokens=60, overlap_tokens=10)
    for chunk in result.chunks:
        sections = {
            block.section
            for block in result.structured.blocks
            if block.char_start < chunk.char_end and block.char_end > chunk.char_start
        }
        assert sections == {chunk.section}


def test_long_claim_is_split_but_keeps_claim_number():
    long_claim = "1. A system comprising " + ", ".join(f"a component {i}" for i in range(200)) + "."
    result = process_document("c.txt", f"CLAIMS\n\n{long_claim}".encode(), max_tokens=100)
    assert len(result.chunks) > 1
    assert all(c.meta.get("claim_number") == 1 for c in result.chunks)
    assert all(c.token_count <= 100 for c in result.chunks)


def test_consecutive_chunks_overlap():
    sentences = " ".join(f"Sentence number {i} describes the coolant loop." for i in range(40))
    result = process_document("o.txt", sentences.encode(), max_tokens=60, overlap_tokens=15)
    assert len(result.chunks) > 2
    for previous, current in zip(result.chunks, result.chunks[1:], strict=False):
        assert current.char_start < previous.char_end  # shared text


def test_fixed_strategy_ignores_structure():
    result = process_document("b.txt", BATTERY, strategy="fixed", max_tokens=100, overlap_tokens=20)
    assert all(c.meta["kind"] == "window" for c in result.chunks)
    # windows cross section boundaries, unlike section-aware chunks
    assert any("CLAIMS" in c.text for c in result.chunks)


def test_overlap_must_be_smaller_than_chunk():
    structured = structure_document([Page(None, ["Some text here."])])
    with pytest.raises(ValueError):
        chunk_document(structured, max_tokens=50, overlap_tokens=50)


def test_figure_abbreviation_does_not_split_sentences():
    result = process_document(
        "f.txt", b"As shown in FIG. 1, the pack has cells. " * 30, max_tokens=50, overlap_tokens=0
    )
    assert not any(c.text.startswith("1,") for c in result.chunks)


# ------------------------------------------------------------------ embeddings


def test_fake_embeddings_are_deterministic_normalised_and_meaningful():
    embedder = FakeEmbedder(dim=256)
    a, b, c = embedder.embed_documents(
        ["battery coolant temperature", "battery temperature sensor", "wireless charging coil"]
    )
    assert a == embedder.embed_documents(["battery coolant temperature"])[0]
    assert math.isclose(sum(v * v for v in a), 1.0, rel_tol=1e-9)

    def dot(x, y):
        return sum(i * j for i, j in zip(x, y, strict=True))

    assert dot(a, b) > dot(a, c)  # shared words -> more similar


def test_local_embedder_rejects_wrong_dimension(monkeypatch):
    class FakeSentenceTransformer:
        def __init__(self, name):
            pass

        def get_embedding_dimension(self):
            return 384

    fake_module = types.SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    with pytest.raises(ConfigurationError, match="384"):
        LocalEmbedder("small-model", dim=1024).embed_query("hello")


def test_e5_models_get_query_and_passage_prefixes():
    embedder = LocalEmbedder("intfloat/multilingual-e5-large", dim=1024)
    assert (embedder._query_prefix, embedder._passage_prefix) == ("query: ", "passage: ")
    assert LocalEmbedder("BAAI/bge-m3", dim=1024)._query_prefix == ""


class _Response:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


def test_api_embedder_parses_and_orders_results(monkeypatch):
    body = {"data": [{"index": 1, "embedding": [0.0, 2.0]}, {"index": 0, "embedding": [3.0, 0.0]}]}
    monkeypatch.setattr(embeddings_module.httpx, "post", lambda *a, **k: _Response(200, body))
    embedder = OpenAICompatibleEmbedder("https://example.test/v1", "key", "m", dim=2)
    assert embedder.embed_documents(["first", "second"]) == [[1.0, 0.0], [0.0, 1.0]]


def test_api_embedder_retries_then_fails_cleanly(monkeypatch):
    calls = []
    monkeypatch.setattr(
        embeddings_module.httpx, "post", lambda *a, **k: calls.append(1) or _Response(503)
    )
    monkeypatch.setattr(embeddings_module.time, "sleep", lambda s: None)
    embedder = OpenAICompatibleEmbedder("https://example.test/v1", "key", "m", dim=2)
    with pytest.raises(ExternalServiceError):
        embedder.embed_documents(["text"])
    assert len(calls) == 3


def test_api_embedder_requires_key():
    with pytest.raises(ConfigurationError):
        OpenAICompatibleEmbedder("https://example.test/v1", "", "m", dim=2)


# ------------------------------------------------------------------ filenames


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("../../etc/passwd.txt", "passwd.txt"),
        ("C:\\Users\\me\\patent.pdf", "patent.pdf"),
        ("bad\x00name\n.pdf", "badname.pdf"),
        ("", "untitled"),
        (None, "untitled"),
    ],
)
def test_filename_sanitising(raw, clean):
    assert sanitize_filename(raw) == clean


def test_very_long_filename_keeps_extension():
    name = sanitize_filename("a" * 400 + ".pdf")
    assert len(name) == 255 and name.endswith(".pdf")
