export interface StrategyConstructor {
  new (): Strategy;
  STRATEGY_NAME: string;
  STRATEGY: string;
}

export abstract class Strategy {
  static MAX_LENGTH = 12;

  get MAX_LENGTH() {
    return Strategy.MAX_LENGTH;
  }

  get SYSTEM_PROMPT() {
    return `You generate brandable names for software products. Return exactly one JSON object with this shape: {"product_names":["name1","name2"]}. Return exactly the requested number of names. Every name must be a non-empty string with fewer than ${this.MAX_LENGTH} characters. Names must be unique, including capitalization differences. Use plain strings without spaces when possible. Do not add explanations, markdown, or extra JSON fields.`;
  }

  get USER_PROMPT() {
    return `Generate exactly {count} product names.\nProduct: {product_description}\nIdea words: {keywords}\nNaming approach: {strategy}\nPrefer memorable, pronounceable names that feel like real software brands. Treat the idea words as inspiration, not words that must appear literally. Avoid repetitive patterns and minor spelling variations. Check every name against the length and uniqueness rules.`;
  }

  getUserPrompt(count: number, productDescription: string, keywords: string): string {
    // 2. Dynamically access the static property of whichever subclass called this
    const strategyClass = this.constructor as StrategyConstructor;
    const strategyText = strategyClass.STRATEGY;

    if (!strategyText) {
      throw new Error(`${this.constructor.name} must define a static STRATEGY property`);
    }

    return this.USER_PROMPT.replace("{count}", count.toString())
      .replace("{product_description}", productDescription)
      .replace("{keywords}", keywords)
      .replace("{strategy}", strategyText);
  }
}

// 3. Convert all subclass properties to `static`
export class ForgeMintStrategy extends Strategy {
  static STRATEGY_NAME = "forge_mint";
  static STRATEGY =
    "Create concise compound names inspired by building, crafting, syntax, tokens, and software development. Combine two concepts only when the result sounds natural. Avoid repeatedly attaching Forge, Mint, Dev, Base, or IO to every name. Prefer strong, simple names over long combinations.";
}

export class AbstractEvocativeStrategy extends Strategy {
  static STRATEGY_NAME = "abstract_evocative";
  static STRATEGY =
    "Invent short, distinctive brand names that evoke discovery, memory, identity, creativity, or a spark of inspiration. Use natural syllables and pleasing sound combinations. Names may be coined words but should be easy to pronounce after reading them once. Avoid random letter strings and obvious dictionary-word combinations.";
}

export class DeveloperSyntaxStrategy extends Strategy {
  static STRATEGY_NAME = "developer_syntax";
  static STRATEGY =
    "Create clever names using concepts from code, syntax, tokens, functions, identifiers, variables, and developer workflows. Use subtle technical wordplay, compact portmanteaus, or double meanings. Make each name understandable to a software engineer without becoming an overly literal technical term. Do not simply concatenate two supplied keywords.";
}

export class LinguisticTwistStrategy extends Strategy {
  static STRATEGY_NAME = "linguistic_twist";
  static STRATEGY =
    "Create compact coined names using subtle vowel changes, syllable blending, consonant substitutions, or shortened words. Every name must remain easy to read and pronounce. Avoid excessive missing vowels, random consonants, and unnecessary letters such as repeated x, z, or y. The result should look intentional, not misspelled.";
}

export class MinimalistStrategy extends Strategy {
  static STRATEGY_NAME = "minimalist";
  static STRATEGY =
    "Generate short, clean names that are easy to spell, say, and remember. Prefer one compact word, a natural coined word, or a subtle two-concept blend. Avoid technical jargon, hyphens, numbers, generic startup suffixes, and long compounds. Optimize for simplicity and recall.";
}

export class MetaphorStrategy extends Strategy {
  static STRATEGY_NAME = "metaphor";
  static STRATEGY =
    "Use metaphors related to discovery, sparks, workshops, identity, seeds, signals, maps, and creation. Transform these ideas into concise software brand names rather than using the metaphor literally every time. Aim for names that create a clear mental image and feel natural.";
}

export class PortmanteauStrategy extends Strategy {
  static STRATEGY_NAME = "portmanteau";
  static STRATEGY =
    "Blend parts of two meaningful words into one compact coined name. The source words may relate to naming, creativity, software, identity, or discovery. Preserve enough of the original sounds to make the blend memorable. Each blend must sound natural when spoken aloud. Do not just append a suffix to a complete keyword.";
}

export class SemanticStrategy extends Strategy {
  static STRATEGY_NAME = "semantic";
  static STRATEGY =
    "Identify the core benefit of the product and generate names that communicate it indirectly but clearly. Explore ideas such as finding, creating, choosing, checking, and discovering identity. Favor meaningful, memorable names over arbitrary letter combinations. Avoid generic names that could describe almost any software product.";
}

export class BalancedStrategy extends Strategy {
  static STRATEGY_NAME = "balanced";
  static STRATEGY =
    "Generate a diverse set of brandable software names. Explore different approaches across the batch: a natural compound, a coined word, a technical pun, a metaphor, a word blend, and a simple memorable name. Do not repeat the same naming pattern. Every candidate must stand on its own and sound like a plausible product brand.";
}

export class MythologicalStrategy extends Strategy {
  static STRATEGY_NAME = "mythological";
  static STRATEGY =
    "Generate distinctive brand names drawn from actual world mythology and folklore, including figures, beings, creatures, artifacts, and culturally significant concepts. Analyze the product description first, identifying its purpose, core capabilities, audience, and desired identity. Select names whose authentic stories, roles, attributes, or symbolism meaningfully relate to that context. Relevance is mandatory: do not include a name merely because it is famous, powerful, or sounds appealing. Explore diverse traditions and lesser-known references; avoid overusing popular deities, alternate names for the same figure, and unrelated mythological name lists. Preserve recognizable, authentic names. Exclude ordinary English words, fabricated mythological-sounding names, and weak or forced associations. Prioritize semantic relevance, distinctiveness, pronunciation, and brandability over quantity. Each name should pass: 1. Mythological authenticity: Is this a real, traceable reference? 2. Product relevance: Is there a meaningful connection to the product's purpose? 3. Brandability: Is it memorable, pronounceable, and distinctive? 4. Redundancy: Does it duplicate another candidate's identity or naming pattern?";
}

// 4. Strongly type the export array
export const STRATEGIES: StrategyConstructor[] = [
  BalancedStrategy,
  SemanticStrategy,
  PortmanteauStrategy,
  MetaphorStrategy,
  MinimalistStrategy,
  LinguisticTwistStrategy,
  DeveloperSyntaxStrategy,
  AbstractEvocativeStrategy,
  ForgeMintStrategy,
  MythologicalStrategy,
];
