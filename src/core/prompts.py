"""Centralized AI prompts, style/glossary enhancements, and response cleanup."""

from __future__ import annotations

import json
import re
from typing import Mapping, Sequence

STYLE_GUIDANCE: dict[str, str] = {
    "Santai (Default)": (
        "Your tone MUST be casual, relaxed, and colloquial, like everyday conversation between normal people. "
        "Use natural phrasing, contractions, and avoid stiff or textbook-like wording. "
        "Keep it light and friendly, suitable for general manga dialogue."
    ),
    "Formal (Ke Atasan)": (
        "Your tone MUST be formal, polite, and respectful, as if addressing a superior, elder, or teacher. "
        "Avoid slang or overly casual phrasing. "
        "Honorifics, polite endings, and respectful language should be preserved where appropriate."
    ),
    "Akrab (Ke Teman/Pacar)": (
        "Your tone MUST be intimate, playful, and very casual, suitable for close friends or romantic partners. "
        "Use warm, affectionate, or teasing expressions where natural. "
        "Convey emotional closeness, and allow a bit of informality, slang, or cuteness if it fits the context."
    ),
    "Vulgar/Dewasa (Adegan Seks)": (
        "Your tone MUST be explicit, vulgar, and direct, suitable for an adult or sexual scene. "
        "Do not soften or censor unless absolutely required by the target language. "
        "Use raw, straightforward words for sexual acts or body parts, while keeping the flow natural. "
        "The style should feel raw and intense, not clinical or overly polite."
    ),
    "Sesuai Konteks Manga": (
        "Analyze the text carefully and adjust your tone to best match the likely context of the manga scene. "
        "- For comedy: be witty, light, and playful. "
        "- For drama: be serious, emotional, and impactful. "
        "- For action: be sharp, concise, and energetic. "
        "- For horror: be tense, eerie, and unsettling. "
        "Always aim for immersion: the translation should feel like it belongs naturally in the scene."
    ),
}

FURIGANA_RULE = (
    "If Japanese input contains kanji with parentheses like 漢字(かんじ) or word(reading), "
    "treat the text inside parentheses as a furigana/reading aid unless it is clearly an explanatory note — "
    "translate the main word naturally (e.g. 勇者(ゆうしゃ) -> 'Hero', not 'Yuusha'), "
    "and only keep parentheses when they are genuine explanatory dialogue notes."
)

JAPANESE_TERMS_RULE = (
    "Keep Japanese familial/age address terms and honorifics in natural Romaji instead of translating them into "
    "Paman/Om/Oom/Uncle, Bibi/Tante/Aunt, Kakak/Abang/Brother/Sister, Kakek/Grandpa, or Nenek/Grandma "
    "(unless overridden in the Glossary below):\n"
    "  * Keep as Romaji: おじさん/おじちゃん -> Ojisan/Oji-chan; おばさん/おばちゃん -> Oba-san/Oba-chan; "
    "お兄ちゃん/お兄さん/兄貴 -> Onii-chan/Onii-san/Aniki; お姉ちゃん/お姉さん/姉貴 -> Onee-chan/Onee-san/Aneki; "
    "おじいさん/じいさん/じいちゃん -> Ojiisan/Jii-san/Jii-chan; おばあさん/ばあさん/ばあちゃん -> Obaasan/Baa-san/Baa-chan; "
    "and honorifics/titles (-san, -kun, -chan, -sama, Senpai, Sensei, Kohai).\n"
    "  * If the input already uses these romanized terms (e.g. Ojisan, Onii-chan, Onee-chan, Oba-san, Jii-san), preserve them.\n"
    "  * EXCEPTION — Parents MUST still be translated naturally into the target language: "
    "お父さん/父さん/父/パパ -> Ayah/Papa (or Father/Dad); お母さん/母さん/母/ママ -> Ibu/Mama (or Mother/Mom)."
)

_THINK_BLOCK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)
_CODE_FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_-]+)?\s*\n?([\s\S]*?)\n?```")
_CJK_CHAR_CLASS = r"\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af"
_VERTICAL_DOT_LEADER_RE = re.compile(r"[\uFE19\u22EE\u22EF\u2025]+|・{3,}|•{3,}")
_STANDALONE_ELLIPSIS_BEFORE_CJK_RE = re.compile(
    rf"(?m)^([ \t]*)(?:…+|[:：;；]+)\s*\n\s*(?=[{_CJK_CHAR_CLASS}])"
)
_LEADING_COLON_OR_DOTS_CJK_RE = re.compile(
    rf"(?m)^([ \t]*)(?:[:：;；]+|\.{2,})[ \t]*(?=[{_CJK_CHAR_CLASS}])"
)
_TRAILING_COLON_CJK_Z_RE = re.compile(
    rf"(?<=[{_CJK_CHAR_CLASS}])[ \t]*[:：]+(?=\s*\Z)"
)
_COLLAPSE_MULTI_ELLIPSIS_RE = re.compile(r"…{2,}")
_INLINE_HEART_EMOTICON_RE = re.compile(
    r"(?<=[^\s♡♥❤❥❣💕💖💗💘💙💚💛💜🖤🤍\uFE0F])[ \t]*([♡♥❤❥❣💕💖💗💘💙💚💛💜🖤🤍][\uFE0F♡♥❤❥❣💕💖💗💘💙💚💛💜🖤🤍]*)"
)


def format_heart_emoticon_lines(text: str) -> str:
    """Place trailing/inline heart emoticons (e.g. 'OSSAN♡') on their own line ('OSSAN\\n♡')."""
    if not isinstance(text, str) or not text:
        return "" if not isinstance(text, str) else text
    return _INLINE_HEART_EMOTICON_RE.sub(r"\n\1", text)


def normalize_manga_ocr_text(text: str) -> str:
    """Normalize vertical manga ellipsis leaders (⋮, ︙, leading : before kanji/kana) to '…'."""
    if not isinstance(text, str) or not text:
        return "" if not isinstance(text, str) else text
    out = _VERTICAL_DOT_LEADER_RE.sub("…", text)
    out = _STANDALONE_ELLIPSIS_BEFORE_CJK_RE.sub(r"\1…", out)
    out = _LEADING_COLON_OR_DOTS_CJK_RE.sub(r"\1…", out)
    out = _TRAILING_COLON_CJK_Z_RE.sub("…", out)
    out = _COLLAPSE_MULTI_ELLIPSIS_RE.sub("…", out)
    return out


def clean_ai_text_output(text: str) -> str:
    """Strip reasoning <think> blocks and outer markdown code fences from AI text."""
    if not isinstance(text, str):
        return ""
    cleaned = _THINK_BLOCK_RE.sub("", text).strip()
    fence_match = _CODE_FENCE_RE.fullmatch(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return format_heart_emoticon_lines(cleaned)


def extract_chat_completion_text(data: Mapping | None) -> str:
    """Extract raw assistant text from an OpenAI-compatible chat completion JSON dict."""
    if not isinstance(data, Mapping):
        return ""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    msg = first.get("message", {}) if isinstance(first, Mapping) else {}
    content = msg.get("content") if isinstance(msg, Mapping) else None
    if isinstance(content, list):
        return "".join(
            part.get("text", "") for part in content if isinstance(part, Mapping)
        )
    if isinstance(content, str):
        return content
    return ""


def build_ocr_prompt(lang: str = "General/Multi-Language") -> str:
    """Build strict transcription-only OCR prompt tailored for manga crops."""
    if lang == "Japanese":
        return (
            "Task: Optical Character Recognition (OCR) for Japanese manga text.\n"
            "Input: a cropped manga text image.\n"
            "Output: ONLY the transcribed original Japanese text in natural manga reading order "
            "(for vertical columns, read top-to-bottom within each column from right to left).\n\n"
            "Rules:\n"
            "- Transcribe verbatim; NEVER translate, explain, summarize, or add commentary.\n"
            "- Do NOT wrap output in markdown or code blocks.\n"
            "- Keep original line breaks and punctuation (。, 、, …, !, ?).\n"
            "- Keep short interjections or symbols accurately (e.g. っ, …, !?).\n"
            "- Vertical ellipses (︙, ⋮, or 2-3 vertically stacked dots above/below kanji like ⋮俺) MUST be transcribed as '…' (e.g. '…俺'), NEVER as a colon ':' or '：'.\n"
            "- Only when small furigana/reading notes appear beside kanji, format as 漢字(note) "
            "(even if vertically aligned). Never wrap unrelated text as [note][kanji].\n"
            "- Return ONLY the plain recognized text."
        )
    if lang == "English":
        return (
            "Task: Optical Character Recognition (OCR) for English comic/manga text.\n"
            "Input: a cropped text image.\n"
            "Output: ONLY the recognized English text in natural reading order (top-to-bottom, left-to-right).\n\n"
            "Rules:\n"
            "- Transcribe verbatim; NEVER translate, explain, or add commentary.\n"
            "- Do NOT output markdown or code blocks.\n"
            "- Maintain original line breaks, casing intent, and punctuation (..., !, ?).\n"
            "- Return ONLY the plain recognized text."
        )
    if lang == "Korean":
        return (
            "Task: Optical Character Recognition (OCR) for Korean (Hangul) manhwa text.\n"
            "Input: a cropped text image.\n"
            "Output: ONLY the recognized Korean text in natural reading order.\n\n"
            "Rules:\n"
            "- Transcribe verbatim; NEVER translate, explain, or add commentary.\n"
            "- Do NOT output markdown or code blocks.\n"
            "- Maintain original line breaks and punctuation.\n"
            "- Return ONLY the plain recognized text."
        )
    if lang == "Chinese":
        return (
            "Task: Optical Character Recognition (OCR) for Chinese manhua text.\n"
            "Input: a cropped text image.\n"
            "Output: ONLY the recognized Chinese text in natural reading order "
            "(for vertical columns, read top-to-bottom from right to left).\n\n"
            "Rules:\n"
            "- Transcribe verbatim; NEVER translate, explain, or add commentary.\n"
            "- Do NOT output markdown or code blocks.\n"
            "- Maintain original line breaks and punctuation.\n"
            "- Return ONLY the plain recognized text."
        )
    return (
        "Task: Optical Character Recognition (OCR) for manga/comic text (Japanese, Korean, Chinese, or English).\n"
        "Input: a cropped text image.\n"
        "Output: ONLY the exact original text in natural reading order.\n\n"
        "Rules:\n"
        "- Transcribe verbatim in the original script; NEVER translate, paraphrase, or add commentary.\n"
        "- For vertical Japanese/Chinese columns, read top-to-bottom from right to left; for horizontal text, left to right.\n"
        "- If Japanese furigana appears next to kanji, write 漢字(furigana).\n"
        "- Vertical ellipses (︙, ⋮, or 2-3 vertically stacked dots above/below kanji like ⋮俺) MUST be transcribed as '…' (e.g. '…俺'), NEVER as a colon ':' or '：'.\n"
        "- Preserve original line breaks, punctuation (。, …, !, ?), and short symbols without inventing words.\n"
        "- Do NOT output markdown or code blocks. Return ONLY plain text."
    )


def build_prompt_enhancements(settings: Mapping | None, glossary: Mapping | None = None) -> str:
    """Build consistent Translation Style + Glossary instructions for AI prompts."""
    cfg = settings if isinstance(settings, Mapping) else {}
    style = str(cfg.get("translation_style") or "Santai (Default)").strip() or "Santai (Default)"
    if style in STYLE_GUIDANCE:
        style_instruction = STYLE_GUIDANCE[style]
    else:
        style_instruction = (
            f"Adopt the requested custom style '{style}', keeping wording natural and consistent for manga dialogue."
        )

    parts = [
        f"\n- Translation Style: {style_instruction}",
        f"\n- Japanese Honorifics & Address Terms: {JAPANESE_TERMS_RULE}",
    ]

    if isinstance(glossary, Mapping) and glossary:
        glossary_lines = [f'  - "{src}" -> "{tgt}"' for src, tgt in glossary.items() if src]
        if glossary_lines:
            parts.append(
                "\n- Character/Term Glossary (ALWAYS use these translations consistently):\n"
                + "\n".join(glossary_lines)
            )

    return "".join(parts)


def build_openrouter_translate_messages(
    text_to_translate: str,
    target_lang: str,
    settings: Mapping | None = None,
    *,
    is_enhanced: bool = False,
    ocr_results: Mapping | None = None,
    glossary: Mapping | None = None,
) -> list[dict[str, str]]:
    """Build [system, user] messages for single/fallback OpenRouter/local translation."""
    cfg = settings if isinstance(settings, Mapping) else {}
    lang = (target_lang or "Indonesian").strip() or "Indonesian"
    mode = cfg.get("mode")
    enhancements = build_prompt_enhancements(cfg, glossary)

    if mode == "info":
        role_intro = (
            f"You are an expert manga translator. Translate the user's text into clear, natural {lang} "
            f"suitable for manga narration boxes or informational notes."
        )
    else:
        role_intro = (
            f"You are an expert manga translator. Translate the user's text into natural, fluent {lang} "
            f"suitable for published manga dialogue, matching the requested style and scene nuance."
        )

    merge_step = (
        f"2. If source text shows multiple OCR candidates (Manga-OCR and Tesseract), merge them into the most accurate reading, silently fix OCR mistakes, and translate into {lang}.\n"
        if is_enhanced and isinstance(ocr_results, Mapping)
        else f"2. Silently fix obvious OCR mistakes, then translate into {lang}.\n"
    )

    system_prompt = (
        f"{role_intro}\n"
        f"1. Automatically detect the source language.\n"
        f"{merge_step}"
        f"3. If the text is already in {lang}, return it unchanged.\n"
        f"4. {FURIGANA_RULE}\n"
        f"5. Treat leading/trailing vertical ellipses (… / ... / ︙ / ⋮, or an OCR-misread leading colon before Japanese text such as ': 俺' or '…俺') as an ellipsis ('...'), e.g. '…俺' -> '...Aku'."
        f"{enhancements}\n"
        f"- Output ONLY the final translation in {lang} as RAW plain text.\n"
        f"- No quotes, no markdown, no code fences, no translator notes, no original text, no extra commentary.\n"
        f"- Preserve line breaks when the input has multiple lines."
    )

    if is_enhanced and isinstance(ocr_results, Mapping):
        manga_ocr_txt = str(ocr_results.get("manga_ocr") or "").strip()
        tess_txt = str(ocr_results.get("tesseract") or "").strip()
        if manga_ocr_txt or tess_txt:
            user_content = (
                "OCR Results:\n"
                f"1. Manga-OCR: {manga_ocr_txt}\n"
                f"2. Tesseract: {tess_txt}"
            )
        else:
            user_content = f"Raw OCR Text:\n{text_to_translate}"
    else:
        user_content = f"Raw OCR Text:\n{text_to_translate}"

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def build_batch_page_translate_prompt(
    texts: Sequence[str],
    target_lang: str,
    settings: Mapping | None = None,
    glossary: Mapping | None = None,
) -> str:
    """Build structured JSON batch translation prompt for ONE manga page in reading order."""
    lang = (target_lang or "Indonesian").strip() or "Indonesian"
    enhancements = build_prompt_enhancements(settings, glossary)
    payload = json.dumps(
        [{"id": i + 1, "text": t} for i, t in enumerate(texts)],
        ensure_ascii=False,
    )
    return (
        f"You are an expert manga translator. Below is a JSON array of dialogue texts extracted from ONE manga page, in reading order.\n"
        f"For each item:\n"
        f"1. Detect the source language and silently correct obvious OCR mistakes.\n"
        f"2. Translate the text into natural, fluent {lang} consistent across the page and matching the style rules below. If it is already in {lang}, keep it as-is.\n"
        f"3. {FURIGANA_RULE}\n"
        f"4. Preserve line breaks inside each string when present. Treat leading/trailing vertical ellipses (… / ... / ︙ / ⋮, or an OCR-misread leading colon before Japanese words such as ': 俺' or '…俺') as an ellipsis ('...'), e.g. '…俺' -> '...Aku'. Do not wrap outputs in quotes or translator notes."
        f"{enhancements}\n\n"
        f"Return ONLY a valid JSON object (no markdown, no explanation) with key \"items\" containing an array of exactly {len(texts)} elements in the same order:\n"
        f"{{\"items\": [{{\"id\": 1, \"translation\": \"<translated text>\"}}, ...]}}\n\n"
        f"Input:\n"
        f"{payload}\n"
    )


__all__ = [
    "STYLE_GUIDANCE",
    "FURIGANA_RULE",
    "JAPANESE_TERMS_RULE",
    "format_heart_emoticon_lines",
    "normalize_manga_ocr_text",
    "clean_ai_text_output",
    "extract_chat_completion_text",
    "build_ocr_prompt",
    "build_prompt_enhancements",
    "build_openrouter_translate_messages",
    "build_batch_page_translate_prompt",
]
