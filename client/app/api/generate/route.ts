import { NextResponse } from 'next/server';

// Match this to the schema you used in gen.py
const jsonSchema = {
  name: "product_names",
  strict: true,
  schema: {
    type: "object",
    properties: {
      product_names: {
        type: "array",
        items: { type: "string" },
        description: "A list of unique software product names under 12 characters."
      }
    },
    required: ["product_names"],
    additionalProperties: false
  }
};

export async function POST(req: Request) {
  try {
    const { description, keywords, count, strategy } = await req.json();

    const systemPrompt = "You generate brandable names for software products. Return exactly one JSON object with this shape: {\"product_names\":[\"name1\"]}. Do not add explanations, markdown, or extra JSON fields.";
    
    const userPrompt = `Generate exactly ${count} product names.
Product: ${description}
Idea words: ${keywords}
Naming approach: ${strategy}
Prefer memorable, pronounceable names that feel like real software brands.`;

    const payload = {
      model: "unsloth/Qwen3.5-4B-GGUF:Q4_K_M", // Matches your local model
      temperature: 0.7,
      max_tokens: 4096, // Prevents truncation
      response_format: { type: "json_schema", json_schema: jsonSchema },
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt }
      ],
      stream: false,
    };

    const response = await fetch(process.env.LLM_TUNNEL_URL!, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Only needed if you locked down the tunnel with Cloudflare Access
        'CF-Access-Client-Id': process.env.CF_ACCESS_CLIENT_ID || '',
        'CF-Access-Client-Secret': process.env.CF_ACCESS_CLIENT_SECRET || ''
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("LLM API Error:", errorText);
      return NextResponse.json({ error: "Name generation failed at the edge" }, { status: response.status });
    }

    const data = await response.json();
    const rawContent = data.choices[0].message.content;
    const parsedData = JSON.parse(rawContent);

    return NextResponse.json({ names: parsedData.product_names });

  } catch (error) {
    console.error("Route Handler Error:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}