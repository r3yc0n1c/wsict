from abc import ABC

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
    "tool",
    "product",
    "software",
    "name",
    "names",
    "generate",
    "using",
    "that",
    "which",
    "your",
}


class Strategy(ABC):
    """Base class for product naming strategies."""

    MAX_LENGTH = 12
    MAX_LENGHT = MAX_LENGTH  # Backwards compatibility with benchmark scripts.

    STRATEGY = ""
    STRATEGY_NAME = "base"

    def __init__(self):
        self.MAX_LENGTH = type(self).MAX_LENGTH
        self.MAX_LENGHT = self.MAX_LENGTH

        # Keep the output contract consistent across all strategies.
        self.SYSTEM_PROMPT = (
            "You generate brandable names for software products. "
            f"Return exactly one JSON object with this shape: "
            '{{"product_names":["name1","name2"]}}. '
            "Return exactly the requested number of names. "
            "Every name must be a non-empty string with fewer than "
            f"{self.MAX_LENGTH} characters. "
            "Names must be unique, including capitalization differences. "
            "Use plain strings without spaces when possible. "
            "Do not add explanations, markdown, or extra JSON fields."
        )

        self.USER_PROMPT = (
            "Generate exactly {count} product names.\n"
            "Product: {product_description}\n"
            "Idea words: {keywords}\n"
            "Naming approach: {strategy}\n"
            "Prefer memorable, pronounceable names that feel like "
            "real software brands. Treat the idea words as inspiration, "
            "not words that must appear literally. "
            "Avoid repetitive patterns and minor spelling variations. "
            "Check every name against the length and uniqueness rules."
        )

    def get_user_prompt(
        self,
        count: int,
        product_description: str,
        keywords: str,
    ) -> str:
        if not self.STRATEGY:
            raise NotImplementedError(f"{type(self).__name__} must define STRATEGY")

        return self.USER_PROMPT.format(
            count=count,
            product_description=product_description,
            keywords=keywords,
            strategy=self.STRATEGY,
        )


class ForgeMintStrategy(Strategy):
    """
    Compound words with a strong developer-tool identity.
    Focus: clarity and immediate relevance.
    """

    STRATEGY_NAME = "forge_mint"
    STRATEGY = (
        "Create concise compound names inspired by building, crafting, "
        "syntax, tokens, and software development. Combine two concepts "
        "only when the result sounds natural. Avoid repeatedly attaching "
        "Forge, Mint, Dev, Base, or IO to every name. "
        "Prefer strong, simple names over long combinations."
    )


class AbstractEvocativeStrategy(Strategy):
    """
    Invented names with a modern startup feel.
    Focus: brandability rather than literal description.
    """

    STRATEGY_NAME = "abstract_evocative"
    STRATEGY = (
        "Invent short, distinctive brand names that evoke discovery, "
        "memory, identity, creativity, or a spark of inspiration. "
        "Use natural syllables and pleasing sound combinations. "
        "Names may be coined words but should be easy to pronounce "
        "after reading them once. Avoid random letter strings and "
        "obvious dictionary-word combinations."
    )


class DeveloperSyntaxStrategy(Strategy):
    """
    Clever naming based on developer culture.
    Focus: technical meaning and wordplay.
    """

    STRATEGY_NAME = "developer_syntax"
    STRATEGY = (
        "Create clever names using concepts from code, syntax, tokens, "
        "functions, identifiers, variables, and developer workflows. "
        "Use subtle technical wordplay, compact portmanteaus, or "
        "double meanings. Make each name understandable to a software "
        "engineer without becoming an overly literal technical term. "
        "Do not simply concatenate two supplied keywords."
    )


class LinguisticTwistStrategy(Strategy):
    """
    Modified words and compact coined spellings.
    Focus: distinctive spelling while remaining readable.
    """

    STRATEGY_NAME = "linguistic_twist"
    STRATEGY = (
        "Create compact coined names using subtle vowel changes, "
        "syllable blending, consonant substitutions, or shortened words. "
        "Every name must remain easy to read and pronounce. "
        "Avoid excessive missing vowels, random consonants, and "
        "unnecessary letters such as repeated x, z, or y. "
        "The result should look intentional, not misspelled."
    )


class MinimalistStrategy(Strategy):
    """
    Simple, clean, low-friction brand names.
    Focus: short names with strong recall.
    """

    STRATEGY_NAME = "minimalist"
    STRATEGY = (
        "Generate short, clean names that are easy to spell, say, "
        "and remember. Prefer one compact word, a natural coined word, "
        "or a subtle two-concept blend. Avoid technical jargon, "
        "hyphens, numbers, generic startup suffixes, and long compounds. "
        "Optimize for simplicity and recall."
    )


class MetaphorStrategy(Strategy):
    """
    Names based on imagery and metaphor.
    Focus: evocative identity.
    """

    STRATEGY_NAME = "metaphor"
    STRATEGY = (
        "Use metaphors related to discovery, sparks, workshops, "
        "identity, seeds, signals, maps, and creation. Transform "
        "these ideas into concise software brand names rather than "
        "using the metaphor literally every time. Aim for names "
        "that create a clear mental image and feel natural."
    )


class PortmanteauStrategy(Strategy):
    """
    Blended words.
    Focus: novel names with a recognizable source.
    """

    STRATEGY_NAME = "portmanteau"
    STRATEGY = (
        "Blend parts of two meaningful words into one compact coined "
        "name. The source words may relate to naming, creativity, "
        "software, identity, or discovery. Preserve enough of the "
        "original sounds to make the blend memorable. Each blend "
        "must sound natural when spoken aloud. Do not just append "
        "a suffix to a complete keyword."
    )


class SemanticStrategy(Strategy):
    """
    Names based on product purpose.
    Focus: communicate the benefit without being generic.
    """

    STRATEGY_NAME = "semantic"
    STRATEGY = (
        "Identify the core benefit of the product and generate names "
        "that communicate it indirectly but clearly. Explore ideas "
        "such as finding, creating, choosing, checking, and discovering "
        "identity. Favor meaningful, memorable names over arbitrary "
        "letter combinations. Avoid generic names that could describe "
        "almost any software product."
    )


class BalancedStrategy(Strategy):
    """
    Mixed naming approaches.
    Focus: diversity across the complete batch.
    """

    STRATEGY_NAME = "balanced"
    STRATEGY = (
        "Generate a diverse set of brandable software names. Explore "
        "different approaches across the batch: a natural compound, "
        "a coined word, a technical pun, a metaphor, a word blend, "
        "and a simple memorable name. Do not repeat the same naming "
        "pattern. Every candidate must stand on its own and sound "
        "like a plausible product brand."
    )


STRATEGIES = [
    BalancedStrategy,
    SemanticStrategy,
    PortmanteauStrategy,
    MetaphorStrategy,
    MinimalistStrategy,
    LinguisticTwistStrategy,
    DeveloperSyntaxStrategy,
    AbstractEvocativeStrategy,
    ForgeMintStrategy
]
