import Anthropic from "@anthropic-ai/sdk";
import type { LeadSource } from "@/lib/supabase/types";
import { FIRST_RESPONSE_SYSTEM_PROMPT } from "./system-prompt";

export interface LeadContext {
  name: string | null;
  source: LeadSource;
}

/** Generates the first-response SMS draft for a new lead. */
export interface FirstResponseGenerator {
  generate(context: LeadContext): Promise<string>;
}

const DEFAULT_MODEL = "claude-haiku-4-5-20251001";

export class ClaudeFirstResponseGenerator implements FirstResponseGenerator {
  private client: Anthropic;
  private model: string;

  constructor(apiKey: string, model: string = DEFAULT_MODEL) {
    this.client = new Anthropic({ apiKey });
    this.model = model;
  }

  async generate(context: LeadContext): Promise<string> {
    const message = await this.client.messages.create({
      model: this.model,
      max_tokens: 200,
      system: FIRST_RESPONSE_SYSTEM_PROMPT,
      messages: [
        {
          role: "user",
          content: `New lead just came in. Name: ${context.name ?? "unknown"}. Came in via: ${context.source.replace("_", " ")}. Draft the text.`,
        },
      ],
    });

    const textBlock = message.content.find((block) => block.type === "text");
    if (!textBlock || textBlock.type !== "text") {
      throw new Error("Model returned no text content");
    }
    return textBlock.text.trim();
  }
}
