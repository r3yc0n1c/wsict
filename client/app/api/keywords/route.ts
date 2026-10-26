import { NextResponse } from "next/server";
import { extractKeywords } from "@/lib/keywords";

export async function POST(req: Request) {
  try {
    const { description } = await req.json();

    if (!description || typeof description !== "string" || !description.trim()) {
      return NextResponse.json({ error: "Product description is required" }, { status: 400 });
    }

    const apiUrl = process.env.LLM_API_BASE_URL;
    const apiKey = process.env.LLM_API_KEY;
    const model = process.env.LLM_MODEL || "unsloth/Qwen3.5-4B-GGUF:Q4_K_M";

    const keywords = await extractKeywords({
      productDescription: description,
      apiUrl,
      apiKey,
      model,
    });

    return NextResponse.json({ keywords });
  } catch (error) {
    console.error("Keywords extraction error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to extract keywords" },
      { status: 500 },
    );
  }
}
