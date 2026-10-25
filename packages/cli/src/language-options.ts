import { InvalidArgumentError } from "commander";

export type WritingLanguage = "ko" | "zh" | "en";

/** CLI input must never silently turn an unsupported language into Chinese. */
export function parseWritingLanguage(value: string): WritingLanguage {
  const normalized = value.trim().toLowerCase().replace(/_/g, "-");
  const match = normalized.match(/^(ko|zh|en)(?:-[a-z0-9]+)*$/);
  if (!match) throw new InvalidArgumentError("집필 언어는 ko(한국어), zh(중국어), en(영어) 중에서 선택하세요.");
  return match[1] as WritingLanguage;
}
