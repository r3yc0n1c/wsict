const schema = {
  name: "keywords",
  strict: true,
  schema: {
    type: "object",
    properties: {
      keywords: {
        type: "array",
        items: { type: "string" },
        description: "A list of unique 8-15 keywords related to the product description.",
      },
    },
    required: ["keywords"],
    additionalProperties: false,
  },
};

const SYSTEM_PROMPT = `
You are a product naming research assistant.

Extract 8-15 concise, meaningful keywords from the provided
software product description to help generate distinctive names.

Rules:
- Identify the core purpose, audience, features, and benefits.
- Include functional, conceptual, and evocative keywords.
- Prefer specific terms over generic words like app, software,
  platform, and tool.
- Use lowercase strings.
- Remove duplicates, filler words, and irrelevant concepts.
- Do not invent features or claims.
- Return ONLY a valid JSON array of strings.
- Do not include markdown or explanations.
`.trim();

export interface ExtractKeywordsParams {
  productDescription: string;
  apiUrl?: string;
  model?: string;
  apiKey?: string;
  temperature?: number;
}

export async function extractKeywords({
  productDescription,
  apiUrl = "http://127.0.0.1:8080/v1/chat/completions",
  model = "default-model",
  apiKey = "",
  temperature = 0.7,
}: ExtractKeywordsParams): Promise<string[]> {
  if (!productDescription.trim()) {
    throw new Error("Product description cannot be empty.");
  }

  const payload = {
    model,
    temperature,
    response_format: { type: "json_schema", json_schema: schema },
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      {
        role: "user",
        content: `Extract 8-15 keywords from this product description:\n\n${productDescription.trim()}`,
      },
    ],
  };

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  // Adding a standard AbortController for a 90s timeout equivalent
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 90000);

  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`LLM API request failed: ${response.status} - ${errText}`);
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content;

    if (!content) {
      throw new Error("Invalid response format from LLM API");
    }

    const parsed = JSON.parse(content);
    const keywords = parsed.keywords;

    if (!Array.isArray(keywords)) {
      throw new Error("Model response must be a JSON array.");
    }

    const cleaned: string[] = [];
    const seen = new Set<string>();

    for (const item of keywords) {
      if (typeof item === "string") {
        const keyword = item.trim().toLowerCase();
        if (keyword && !seen.has(keyword)) {
          seen.add(keyword);
          cleaned.push(keyword);
        }
      }
    }

    return cleaned;
  } finally {
    clearTimeout(timeoutId);
  }
}
