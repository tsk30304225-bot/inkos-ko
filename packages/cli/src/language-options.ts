import { InvalidArgumentError } from "commander";

export type WritingLanguage = "ko" | "zh" | "en";

/** CLI input must never silently turn an unsupported language into Chinese. */
export function parseWritingLanguage(value: string): WritingLanguage {
  const normalized = value.trim().toLowerCase().replace(/_/g, "-");
  const match = normalized.match(/^(ko|zh|en)(?:-[a-z0-9]+)*$/);
  if (!match) throw new InvalidArgumentError("Writing language must be zh, en or ko (집필 언어는 ko·zh·en 중 하나).");
  return match[1] as WritingLanguage;
}
