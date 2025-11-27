import "dotenv/config";
import { GoogleGenAI } from "@google/genai";

// Simple Gemini wrapper using Google's Generative Language REST endpoint.
// NOTE: This is a minimal wrapper and may need to be adapted to any auth (API key / OAuth) you're using.
// Set GEMINI_API_KEY and GEMINI_MODEL in your .env file. Example model: "text-bison-001" or "gemini-pro"

const API_KEY = process.env.GEMINI_API_KEY;
const MODEL = process.env.GEMINI_MODEL || "text-bison-001";

interface RefinementOptions {
  grammar?: boolean;
  funny?: boolean;
  professional?: boolean;
}

export type GeminiResult = {
  text: string;
  fallback: boolean; // true when we returned input due to missing creds/error
  error?: string; // error code or message
  status?: number; // HTTP status if any
};

export async function refineText(
  input: string,
  options?: RefinementOptions
): Promise<GeminiResult> {
  // If there's no GEMINI API key, return the message unchanged as a fallback.
  if (!API_KEY) {
    console.warn(
      "GEMINI_API_KEY is not set — returning original input as fallback."
    );
    return { text: input, fallback: true, error: "no-credentials" };
  }

  // Build a prompt based on options. Apply sensible defaults.
  const grammar = options?.grammar ?? true; // grammar should be applied by default
  const funny = options?.funny ?? false;
  const professional = options?.professional ?? false;

  const rules: string[] = [];
  // Grammar rules
  if (grammar) rules.push("Fix grammar and spelling.");
  else rules.push("Do not modify grammar or spelling.");

  // Tone and emoji rules
  if (professional && funny) {
    // Both requested — keep professional but add a light humorous tone without emojis.
    rules.push(
      "Apply a professional tone and formal register; you may add mild humor but do NOT include any emojis."
    );
  } else if (professional) {
    rules.push("Apply professional tone and no emojis; prefer formal wording.");
  } else if (funny) {
    rules.push(
      "Add humor and lively tone; emojis are allowed and encouraged where appropriate."
    );
  } else {
    rules.push("Keep a neutral and natural tone; do not add emojis.");
  }

  let instructions = `Refine the following text. ${rules.join(" ")}`;
  instructions +=
    " Only modify the text according to the rules and keep the core meaning intact.";
  // Explicit: return only the final text, no commentary or summaries.
  instructions +=
    " IMPORTANT: Return ONLY the final refined text as a single message. Do NOT add any explanations, lists of changes, suggestions, comments, or questions; do NOT ask the user anything.";

  const prompt = `${instructions}\n\nText:\n${input}`;
  // Use official Google GenAI client when possible
  const client = new GoogleGenAI({ apiKey: API_KEY });
  try {
    const response = await client.models.generateContent({
      model: MODEL,
      // Use a single content string for simplicity
      contents: prompt,
      maxOutputTokens: 512,
    } as any);

    // The Google Generative Language API for v1beta2 returns 'candidates' in the `output` object.
    // We try to safely pick something that looks like generated text.
    // Prefer `response.text` if available, else fall back to known nested fields
    const generated =
      (response as any)?.text ||
      (response as any)?.candidates?.[0]?.content ||
      (response as any)?.output?.[0]?.content ||
      (response as any)?.output?.[0]?.text;

    if (!generated) {
      console.warn(
        "Gemini response did not contain any text - returning original"
      );
      return { text: input, fallback: true, error: "no-output" };
    }
    // `generated` could be a string or complex object; coerce to string.
    let text =
      typeof generated === "string" ? generated : JSON.stringify(generated);
    text = text.trim();
    // Remove trailing question sentences (models sometimes append a clarifying question) or prompts
    const sentenceMatches = text.match(/[^.!?]+[.!?]*/g);
    if (Array.isArray(sentenceMatches) && sentenceMatches.length > 1) {
      // Remove any trailing question sentences
      while (
        sentenceMatches.length > 0 &&
        /\?\s*$/.test(sentenceMatches[sentenceMatches.length - 1])
      ) {
        sentenceMatches.pop();
      }
      text = sentenceMatches.join("").trim();
    }

    // Clean up typical model echoes or labels that some models add.
    text = text.replace(/^Refined (message|text)[:\-]\s*/i, "");
    // Remove short meta-lines like 'no grammar change', 'no professionalism', etc. at start/end
    text = text.replace(
      /^(no\s+(grammar|professional|professionalism|funny|emojis|emoji)(\s|$).*)/i,
      ""
    );
    text = text.replace(
      /(no\s+(grammar|professional|professionalism|funny|emojis|emoji)(\s|$).*)$/i,
      ""
    );
    text = text.trim();
    return { text, fallback: false };
  } catch (e) {
    console.error("Error calling Gemini:", e);
    return {
      text: input,
      fallback: true,
      error: (e as Error)?.message || "network-error",
    };
  }
}
