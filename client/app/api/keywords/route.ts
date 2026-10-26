import { NextResponse } from "next/server";
import { extractKeywords } from "@/lib/keywords";
import { isRateLimited, getClientIp } from "@/lib/ratelimit";

export async function POST(req: Request) {
  try {
    const ip = getClientIp(req);
    const { limited, resetInSec } = isRateLimited(ip, 10, 60_000);
    if (limited) {
      return NextResponse.json(
        { error: `Too many keyword requests. Please wait ${resetInSec}s.` },
        {
          status: 429,
          headers: { "Retry-After": resetInSec.toString() },
        },
      );
    }

    const { description } = await req.json();

    if (!description || typeof description !== "string" || !description.trim()) {
      return NextResponse.json({ error: "Product description is required" }, { status: 400 });
    }

    const apiUrl = process.env.LLM_API_BASE_URL! + "v1/chat/completions";
    const apiKey = process.env.LLM_API_KEY!;
    const model = process.env.LLM_MODEL!;

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
