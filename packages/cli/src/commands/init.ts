import { Command } from "commander";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { log, logError } from "../utils.js";
import { initializeProjectDirectory } from "../project-bootstrap.js";
import { parseWritingLanguage, type WritingLanguage } from "../language-options.js";

export const initCommand = new Command("init")
  .description("Initialize an InkOS project (current directory by default)")
  .argument("[name]", "Project name (creates subdirectory). Omit to init current directory.")
  .option("--lang <language>", "Writing language: ko (한국어), zh (Chinese), en (English)", parseWritingLanguage, "ko")
  .action(async (name: string | undefined, opts: { lang: WritingLanguage }) => {
    const projectDir = name ? resolve(process.cwd(), name) : process.cwd();
    try {
      await mkdir(projectDir, { recursive: true });
      await initializeProjectDirectory(projectDir, { language: opts.lang, overwriteSupportFiles: true });
      const ko = opts.lang === "ko";
      log(ko ? `프로젝트를 초기화했습니다: ${projectDir}` : `Project initialized at ${projectDir}`);
      log(ko ? "다음 단계:" : "Next steps:");
      if (name) log(`  cd ${name}`);
      if (ko) {
        log("  inkos book create --title '새로운 이야기' --genre other --platform other --lang ko");
      } else if (opts.lang === "en") {
        log("  inkos book create --title 'My Novel' --genre progression --platform royalroad --lang en");
      } else {
        log("  inkos book create --title '我的小说' --genre xuanhuan --platform tomato --lang zh");
      }
      log("  inkos write next <book-id>");
    } catch (error) {
      logError(opts.lang === "ko" ? `프로젝트 초기화 실패: ${error}` : `Failed to initialize project: ${error}`);
      process.exit(1);
    }
  });
