import { describe, expect, it } from "vitest";
import { getAppLanguage, normalizeAppLanguage, setAppLanguage, tr } from "./app-language";
import { translateStudioString } from "../hooks/use-i18n";
import { buildBookCreatePayload, defaultBookCreateForm, platformOptionsForLanguage } from "../pages/BookCreate";

describe("Korean Studio", () => {
  it("selects Korean navigation and explicit inline translations without Chinese fallback", () => {
    setAppLanguage(normalizeAppLanguage("ko"));
    expect(getAppLanguage()).toBe("ko");
    expect(translateStudioString("nav.books", "ko")).toBe("작품");
    expect(tr("中文", "English", "한국어")).toBe("한국어");
    expect(tr("中文", "English")).toBe("English");
    setAppLanguage("zh");
  });
  it("submits a Korean book instead of a Chinese default", () => {
    const form = { ...defaultBookCreateForm("ko"), title: "밤 항구", genre: "미스터리", brief: "사라진 장부를 찾는 이야기" };
    expect(platformOptionsForLanguage("ko")).toEqual([{ value: "other", label: "기타 / 직접 설정" }]);
    expect(buildBookCreatePayload(form, "ko")).toMatchObject({ language: "ko", title: "밤 항구", chapterWordCount: 3000, platform: "other" });
  });
});
