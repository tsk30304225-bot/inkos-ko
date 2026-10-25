import { Command } from "commander";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { log, logError } from "../utils.js";
import { initializeProjectDirectory } from "../project-bootstrap.js";
import { parseWritingLanguage, type WritingLanguage } from "../language-options.js";

export const initCommand = new Command("init")
  .description("Initialize an InkOS project (current directory by default)")
  .argument("[name]", "Project name (creates subdirectory). Omit to init current directory.")
  .option("--lang <language>", "Default writing language: zh (Chinese), en (English) or ko (Korean)", parseWritingLanguage, "zh")
  .action(async (name: string | undefined, opts: { lang: WritingLanguage }) => {
    const projectDir = name ? resolve(process.cwd(), name) : process.cwd();

    try {
      await mkdir(projectDir, { recursive: true });
      await initializeProjectDirectory(projectDir, {
        language: opts.lang,
        overwriteSupportFiles: true,
      });

      if (opts.lang === "ko") {
        log(`프로젝트를 초기화했습니다: ${projectDir}`);
        log("");
        log("다음 단계:");
        if (name) log(`  cd ${name}`);
        log("  inkos book create --title '새로운 이야기' --genre light-martial --lang ko");
        log("  # 장르 기준이 있는 값: light-martial(라이트 무협), fantasy(판타지), modern-fantasy(현대판타지). 그 밖의 값은 장르 기준 없이 진행합니다.");
        log("  inkos write next <book-id>");
        return;
      }

      log(`Project initialized at ${projectDir}`);
      log("");
      const isEnglish = opts.lang === "en";
      const exampleCreateLines = isEnglish
        ? ["  inkos book create --title 'My Novel' --genre progression --platform royalroad --lang en"]
        : [
          "  inkos book create --title '我的小说' --genre xuanhuan --platform tomato",
          "  # English project? Re-run with: inkos init --lang en",
        ];
      if (global) {
        log("Global LLM config detected. Ready to go!");
        log("");
        log("Next steps:");
        if (name) log(`  cd ${name}`);
        for (const line of exampleCreateLines) log(line);
      } else {
        log("Next steps:");
        if (name) log(`  cd ${name}`);
        log("  # Option 1: Set global config (recommended, one-time):");
        log("  inkos config set-global --provider openai --base-url <your-api-url> --api-key <your-key> --model <your-model>");
        log("  # Option 2: Edit .env for this project only");
        log("");
        for (const line of exampleCreateLines) log(line);
      }
      log("  inkos write next <book-id>");
    } catch (e) {
      logError(opts.lang === "ko" ? `프로젝트 초기화 실패: ${e}` : `Failed to initialize project: ${e}`);
      process.exit(1);
    }
  });
