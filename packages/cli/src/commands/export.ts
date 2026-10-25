import { Command } from "commander";
import { formatLengthCount, resolveLengthCountingMode, StateManager, writeExportArtifact, ChapterExportSourceError } from "@actalk/inkos-core";
import { join } from "node:path";
import { findProjectRoot, resolveBookId, log, logError } from "../utils.js";

export const exportCommand = new Command("export")
  .description("Export book chapters to a single file")
  .argument("[book-id]", "Book ID (auto-detected if only one book)")
  .option("--format <format>", "Output format (txt, md, epub)", "txt")
  .option("--output <path>", "Output file path")
  .option("--json", "Output JSON metadata")
  .action(async (bookIdArg: string | undefined, opts) => {
    try {
      const root = findProjectRoot();
      const bookId = await resolveBookId(bookIdArg, root);
      const state = new StateManager(root);

      const result = await writeExportArtifact(state, bookId, {
        format: opts.format as "txt" | "md" | "epub",
        outputPath: opts.output ?? join(root, `${bookId}_export.${opts.format}`),
      });

      if (opts.json) {
        log(JSON.stringify({
          bookId,
          chaptersExported: result.chaptersExported,
          totalWords: result.totalWords,
          format: result.format,
          outputPath: result.outputPath,
        }, null, 2));
      } else {
        const book = await state.loadBookConfig(bookId);
        if (book.language === "ko") {
          const length = formatLengthCount(result.totalWords, resolveLengthCountingMode("ko"));
          log(`${result.chaptersExported}개 회차를 내보냈습니다(${length}).`);
          log(`저장 위치: ${result.outputPath}`);
        } else {
          log(`Exported ${result.chaptersExported} chapters (${result.totalWords} words)`);
          log(`Output: ${result.outputPath}`);
        }
      }
    } catch (e) {
      if (opts.json) {
        log(JSON.stringify({ error: String(e), ...(e instanceof ChapterExportSourceError ? {code:e.code,details:e.details} : {}) }));
      } else {
        logError(`Failed to export: ${e}`);
      }
      process.exit(1);
    }
  });
