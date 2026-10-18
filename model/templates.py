from abc import ABC, abstractmethod


class Strategy(ABC):
    SYSTEM_PROMPT: str
    USER_PROMPT: str
    PREFIX: str
    STRATEGY: str
    KEYWORDS: str
    MAX_LENGTH: int

    def __init__(self) -> None:
        super().__init__()

        self.MAX_LENGTH = 12
        
        # Build the system prompt
        self.SYSTEM_PROMPT = (
            "You are an expert brand strategist. Your task is to generate unique "
            "software product names. You must return ONLY a JSON array of strings. "
            f"Do not include any other text, markdown, or explanations. Keep names under {self.MAX_LENGTH} characters."
        )

        self.PREFIX = 'Generate {count} unique product names for a software tool described as: "{product_description}"\n'
        self.KEYWORDS = "Keywords: {keywords}.\n"

        # Build the prompt automatically from subclass constants
        self.USER_PROMPT = self.PREFIX + self.KEYWORDS + self.STRATEGY

    def get_user_prompt(
        self, count: int, product_description: str, keywords: str
    ) -> str:
        """Shared method available to all strategies.
        Formats the subclass's unique USER_PROMPT.
        """

        if not getattr(self, "USER_PROMPT", None):
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'USER_PROMPT'"
            )

        return self.USER_PROMPT.format(
            count=count,
            product_description=product_description,
            keywords=keywords,
        )


class ForgeMintStrategy(Strategy):
    STRATEGY = (
        "Strategy: Combine the keywords with tech-focused suffixes (like -io, -base, -dev) or "
        "blend them together to create a strong, builder-focused identity."
    )


class AbstractEvocativeStrategy(Strategy):
    STRATEGY = (
        "Strategy: Create short (4-8 letters), abstract, highly brandable names that evoke a sense "
        "of 'origin,' 'identity,' 'discovery,' or 'spark.'"
        "They do not need to literally describe naming; "
        "they should sound like a modern, fast tech startup."
    )


class DeveloperSyntaxStrategy(Strategy):
    STRATEGY = (
        "Strategy: Use the provided developer and coding keywords and merge them with concepts of identity and naming."
        "The goal is a clever, slightly nerdy portmanteau or phrase that appeals to software engineers."
    )


class LinguisticTwistStrategy(Strategy):
    STRATEGY = (
        "Strategy: Take the keywords and drop vowels (e.g., Nm, Brnd) or swap letters "
        "(e.g., 'c' to 'k', 'i' to 'y') to create ultra-short, modern spellings that look good next "
        "to a '.dev' domain extension. Ensure they remain pronounceable."
    )
