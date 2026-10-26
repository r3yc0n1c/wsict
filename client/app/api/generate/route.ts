import { NextResponse } from "next/server";
import { STRATEGIES } from "@/lib/templates";

const jsonSchema = {
  name: "product_names",
  strict: true,
  schema: {
    type: "object",
    properties: {
      product_names: {
        type: "array",
        items: { type: "string" },
        description: "A list of unique software product names under 12 characters.",
      },
    },
    required: ["product_names"],
    additionalProperties: false,
  },
};

export async function POST(req: Request) {
  try {
    const { description, keywords, count = 5, strategy = "balanced" } = await req.json();

    if (!description || typeof description !== "string" || !description.trim()) {
      return NextResponse.json({ error: "Product description is required" }, { status: 400 });
    }

    // Cap total names to a maximum of 20
    const safeCount = Math.min(20, Math.max(1, Number(count) || 5));

    const apiUrl = process.env.LLM_API_BASE_URL;
    const apiKey = process.env.LLM_API_KEY;
    const model = process.env.LLM_MODEL;

    const kwString = Array.isArray(keywords) ? keywords.join(", ") : String(keywords || "");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;
    if (process.env.CF_ACCESS_CLIENT_ID) {
      headers["CF-Access-Client-Id"] = process.env.CF_ACCESS_CLIENT_ID;
      headers["CF-Access-Client-Secret"] = process.env.CF_ACCESS_CLIENT_SECRET || "";
    }

    if (strategy === "all") {
      const calls = STRATEGIES.map(async (Strat) => {
        const inst = new Strat();
        const payload = {
          model,
          temperature: 0.7,
          max_tokens: 4096,
          response_format: { type: "json_schema", json_schema: jsonSchema },
          messages: [
            { role: "system", content: inst.SYSTEM_PROMPT },
            { role: "user", content: inst.getUserPrompt(safeCount, description, kwString) },
          ],
          stream: false,
        };
        const res = await fetch(apiUrl, { method: "POST", headers, body: JSON.stringify(payload) });
        if (res.ok) {
          const d = await res.json();
          const parsed = JSON.parse(d.choices?.[0]?.message?.content || "{}");
          return (parsed.product_names as string[]) || [];
        }
        return [];
      });

      const batch = await Promise.all(calls);
      const names = batch.flat();
      return NextResponse.json({ names });
    }

    const StrategyClass = STRATEGIES.find((s) => s.STRATEGY_NAME === strategy) || STRATEGIES[0];
    const inst = new StrategyClass();

    const payload = {
      model,
      temperature: 0.7,
      max_tokens: 4096,
      response_format: { type: "json_schema", json_schema: jsonSchema },
      messages: [
        { role: "system", content: inst.SYSTEM_PROMPT },
        { role: "user", content: inst.getUserPrompt(safeCount, description, kwString) },
      ],
      stream: false,
    };

    const response = await fetch(apiUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("LLM API Error:", errorText);
      return NextResponse.json(
        { error: "Name generation failed from LLM API" },
        { status: response.status },
      );
    }

    const data = await response.json();
    const rawContent = data.choices?.[0]?.message?.content;
    if (!rawContent) {
      return NextResponse.json({ error: "Empty response from LLM" }, { status: 502 });
    }
    const parsedData = JSON.parse(rawContent);

    return NextResponse.json({ names: parsedData.product_names || [] });
  } catch (error) {
    console.error("Route Handler Error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Internal server error" },
      { status: 500 },
    );
  }
}
