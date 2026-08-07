"""
ATS node — computes the ATS compatibility score.

Extracts keywords from the job offer and measures how many
appear in the candidate's CV, producing an ATS score (0-100).
"""

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable

from app.agents.state import AnalyseState
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Stopwords (French + English)
#
# Stored WITHOUT accents: tokens are accent-folded before the lookup, so
# "être" is compared as "etre".
# ---------------------------------------------------------------------------

STOPWORDS: frozenset[str] = frozenset({
    # French — determiners, pronouns, prepositions, conjunctions
    "le", "la", "les", "un", "une", "des", "du", "de", "au", "aux", "ce",
    "cet", "cette", "ces", "son", "sa", "ses", "leur", "leurs", "notre",
    "nos", "votre", "vos", "mon", "ma", "mes", "ton", "ta", "tes", "on",
    "il", "elle", "ils", "elles", "nous", "vous", "je", "tu", "se", "se",
    "qui", "que", "quoi", "dont", "ou", "et", "ni", "or", "car", "mais",
    "donc", "si", "en", "y", "par", "pour", "sur", "sous", "avec", "sans",
    "dans", "chez", "vers", "entre", "apres", "avant", "depuis", "pendant",
    "selon", "afin", "ainsi", "aussi", "alors", "meme", "tout", "tous",
    "toute", "toutes", "autre", "autres", "chaque", "plus", "moins", "tres",
    "bien", "deja", "encore", "toujours", "jamais", "pas", "ne", "non",
    "oui", "cela", "ceci", "celui", "celle", "lui", "eux", "moi", "toi",
    # French — high-frequency verbs (job-ad boilerplate)
    "est", "sont", "etre", "ete", "etait", "sera", "seront", "soit",
    "avoir", "aura", "auront", "avait", "avez", "avons", "ont", "faire",
    "fait", "faites", "fais", "peut", "peux", "pouvez", "pourra", "doit",
    "dois", "devez", "devra", "va", "vas", "vont", "aller", "prendre",
    "prend", "mettre", "met", "existe", "existent", "permet", "permettre",
    "rejoins", "rejoindre", "travailler", "travaille",
    # French — job-ad filler nouns / adjectives
    "poste", "profil", "mission", "missions", "offre", "offres", "entreprise",
    "societe", "equipe", "equipes", "candidat", "candidate", "candidature",
    "recherche", "recherchons", "cherchons", "propose", "proposons", "offrons",
    "rejoindre", "contrat", "salaire", "remuneration", "avantages", "lieu",
    "jour", "jours", "annee", "annees", "mois", "semaine", "temps", "cadre",
    "niveau", "type", "types", "charge", "place", "partir", "besoin",
    "besoins", "nouveau", "nouvelle", "nouveaux", "nouvelles", "grand",
    "grande", "bon", "bonne", "vrai", "vrais", "vraies", "vraie", "propre",
    "general", "generale", "direct", "directe", "quotidien", "possible",
    "notamment", "egalement", "chaque", "reel", "reels", "reelle", "reelles",
    # English — determiners, pronouns, prepositions, conjunctions
    "the", "a", "an", "and", "or", "but", "nor", "so", "yet", "in", "on",
    "at", "to", "for", "of", "with", "without", "from", "by", "as", "into",
    "over", "under", "between", "during", "before", "after", "about",
    "this", "that", "these", "those", "it", "its", "we", "you", "they",
    "he", "she", "our", "your", "their", "his", "her", "them", "us",
    # English — high-frequency verbs / fillers
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "will", "would", "can", "could", "should", "may", "might", "must", "do",
    "does", "did", "get", "got", "make", "makes", "made", "work", "working",
    "role", "team", "company", "job", "position", "candidate", "experience",
    "years", "year", "new", "good", "strong", "able", "well", "also", "more",
    "most", "some", "any", "all", "each", "other", "such", "very", "than",
    "then", "there", "here", "what", "which", "who", "whom", "when", "where",
    "how", "why", "not", "no", "yes", "own", "out", "up", "down", "off",
})

# Short tech tokens worth keeping even though they are under the length floor.
SHORT_TECH_TOKENS: frozenset[str] = frozenset({
    "js", "ts", "go", "ci", "cd", "ui", "ux", "qa", "ia", "ai", "ml", "vr",
    "ar", "bi", "db", "os", "vm", "k8s", "c#", "c++", "3d", "2d",
})

MIN_TOKEN_LENGTH = 3

# Words start with a letter, then allow the punctuation found in tech terms
# ("node.js", "c++", "c#", "ci-cd", "scikit-learn").
_TOKEN_RE = re.compile(r"[a-z][a-z0-9+#._-]*")

# Punctuation that is meaningful inside a token but noise at its edges.
_EDGE_CHARS = "._-"


def fold_accents(text: str) -> str:
    """
    Removes diacritics so accented and unaccented spellings compare equal.

    "développement" -> "developpement", "données" -> "donnees".

    Without this, the tokenizer regex (ASCII-only) splits on the accent and
    silently drops the head of the word: "développement" -> "veloppement".

    Args:
        text: Input text.

    Returns:
        The same text with all combining marks stripped.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def tokenize(text: str) -> list[str]:
    """
    Splits a text into normalized, meaningful tokens.

    - Lowercases and folds accents
    - Keeps tech punctuation inside tokens, trims it at the edges
    - Drops stopwords and tokens shorter than MIN_TOKEN_LENGTH,
      except known short tech terms (js, ci, ux, c++, ...)

    Args:
        text: Input text to tokenize.

    Returns:
        Tokens in order of appearance (duplicates kept, for frequency counts).
    """
    normalized = fold_accents(text.lower())

    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(normalized):
        token = raw.strip(_EDGE_CHARS)
        if not token or token in STOPWORDS:
            continue
        if len(token) < MIN_TOKEN_LENGTH and token not in SHORT_TECH_TOKENS:
            continue
        tokens.append(token)

    return tokens


def token_variants(token: str) -> set[str]:
    """
    Returns the equivalent spellings of a token.

    Lets "node.js" match "nodejs" and "ci-cd" match "cicd", which are the
    same skill written differently in a CV and in a job offer.

    Args:
        token: A normalized token.

    Returns:
        Set containing the token and its punctuation-free form.
    """
    compact = token.replace(".", "").replace("-", "").replace("_", "")
    return {token, compact} if compact else {token}


def extract_keywords(text: str, top_n: int = 40) -> list[str]:
    """
    Extracts the most relevant keywords from a text, ranked by frequency.

    Used for the job offer, where only the dominant requirements matter.

    Args:
        text:  Input text to extract keywords from.
        top_n: Maximum number of keywords to return.

    Returns:
        List of keywords sorted by frequency (most common first).
    """
    counter = Counter(tokenize(text))
    return [word for word, _ in counter.most_common(top_n)]


def extract_vocabulary(text: str) -> set[str]:
    """
    Extracts the FULL set of tokens (and spelling variants) from a text.

    Used for the CV side of the comparison. Ranking the CV by frequency would
    be wrong: a skill like "postgresql" is usually mentioned once, so it would
    never survive a top-N cut and would be reported as missing.

    Args:
        text: Input text.

    Returns:
        Set of every token found, plus its punctuation-free variants.
    """
    vocabulary: set[str] = set()
    for token in tokenize(text):
        vocabulary |= token_variants(token)
    return vocabulary


def compute_ats_score(
    cv_tokens: Iterable[str],
    job_keywords: list[str],
) -> tuple[int, list[str], list[str]]:
    """
    Computes ATS compatibility score by comparing keyword sets.

    The ATS score measures what fraction of job offer keywords
    appear anywhere in the CV.

    Args:
        cv_tokens:    Tokens present in the CV — either a plain keyword list or
                      the variant set returned by extract_vocabulary().
        job_keywords: Ranked keywords extracted from the job offer.

    Returns:
        Tuple of (score, keywords_found, keywords_missing):
        - score:            Integer 0-100
        - keywords_found:   Job keywords present in CV
        - keywords_missing: Job keywords absent from CV
    """
    job_set = set(job_keywords)
    if not job_set:
        return 0, [], []

    cv_vocabulary: set[str] = set()
    for token in cv_tokens:
        cv_vocabulary |= token_variants(token)

    found = sorted(kw for kw in job_set if token_variants(kw) & cv_vocabulary)
    missing = sorted(job_set - set(found))

    score = int(round(len(found) / len(job_set) * 100))
    return min(score, 100), found, missing


def compute_ats_node(state: AnalyseState) -> dict:
    """
    LangGraph node: extracts keywords and computes the ATS score.

    Args:
        state: Pipeline state with cv_text and job_text.

    Returns:
        State updates: job/cv keywords, ATS score, found/missing keywords, SSE event.
    """
    job_keywords = extract_keywords(state["job_text"])
    cv_vocabulary = extract_vocabulary(state["cv_text"])

    score, found, missing = compute_ats_score(cv_vocabulary, job_keywords)

    progress_event = {
        "type": "progress",
        "step": "ats",
        "progress": 35,
        "data": {
            "score_ats": score,
            "keywords_found_count": len(found),
            "keywords_missing_count": len(missing),
        },
    }

    logger.info(
        "ATS node executed",
        extra={
            "score_ats": score,
            "found": len(found),
            "missing": len(missing),
        },
    )

    return {
        "job_keywords": job_keywords,
        # Ranked CV keywords are for display only — matching uses the full vocabulary.
        "cv_keywords": extract_keywords(state["cv_text"]),
        "score_ats": score,
        "keywords_found": found,
        "keywords_missing": missing[:15],  # Limit to top 15 missing keywords
        "stream_events": state.get("stream_events", []) + [progress_event],
    }
