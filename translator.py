import urllib.request
import urllib.parse
import json
import re
import html

CACHE = {}
DICT_CACHE = {}

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for", "with",
    "by", "about", "as", "into", "like", "through", "after", "over", "between", "out",
    "against", "during", "without", "before", "under", "around", "among", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "can", "could", "shall", "should", "will", "would", "may", "might", "must", "i",
    "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "my",
    "your", "his", "their", "our", "its", "this", "that", "these", "those", "what",
    "which", "who", "whom", "whose", "how", "when", "where", "why", "just", "so", "very",
    "not", "no", "yes", "all", "any", "some", "more", "most", "also", "then", "now",
    "get", "go", "make", "take", "come", "see", "know", "think", "look", "want", "give", "use"
}

def clean_text(s: str) -> str:
    """Strip out replacement characters, nulls, and unescape HTML entities."""
    if not s:
        return ""
    s = s.replace('\ufffd', '').replace('\x00', '').strip()
    return html.unescape(s)

def translate_zh_to_en(text: str) -> str:
    text = clean_text(text)
    if not text:
        return ""
    if text in CACHE:
        return CACHE[text]
    
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=zh-CN&tl=en&dt=t&q={urllib.parse.quote(text)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            parts = [p[0] for p in data[0] if p and p[0]]
            res = clean_text("".join(parts))
            if res:
                CACHE[text] = res
                return res
    except Exception:
        # Fallback to MyMemory
        try:
            mm_url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair=zh|en"
            req2 = urllib.request.Request(mm_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req2, timeout=2.5) as resp2:
                data2 = json.loads(resp2.read().decode('utf-8'))
                res = clean_text(data2.get('responseData', {}).get('translatedText', ''))
                if res:
                    CACHE[text] = res
                    return res
        except Exception:
            pass
    return ""

def translate_single_word(word: str) -> str:
    clean_w = word.strip()
    if not clean_w:
        return ""
    if clean_w.lower() in DICT_CACHE:
        return DICT_CACHE[clean_w.lower()]

    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={urllib.parse.quote(clean_w)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            res = clean_text("".join([p[0] for p in data[0] if p and p[0]]))
            DICT_CACHE[clean_w.lower()] = res
            return res
    except Exception:
        return ""

def analyze_learning_card(zh_text: str) -> dict:
    zh_text = clean_text(zh_text)
    if not zh_text:
        return None
    
    en_trans = translate_zh_to_en(zh_text)
    if not en_trans:
        return None

    # Filter candidate words
    raw_words = re.findall(r'\b[a-zA-Z\-]{3,}\b', en_trans)
    candidates = []
    seen = set()
    for w in raw_words:
        w_lower = w.lower()
        if w_lower not in STOP_WORDS and w_lower not in seen:
            seen.add(w_lower)
            candidates.append(w)
            if len(candidates) >= 3:
                break

    keywords = []
    for w in candidates:
        meaning = translate_single_word(w)
        if meaning and meaning.lower() != w.lower():
            keywords.append({
                "word": w,
                "phonetic": "",
                "meaning": meaning
            })

    return {
        "chinese": zh_text,
        "english": en_trans,
        "keywords": keywords
    }
