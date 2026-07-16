import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { getNextLocale, I18nProvider, LanguageSwitcher } from "@cmc/i18n";

describe("ordering language toggle", () => {
  it("renders one current-locale button instead of a segmented switch", () => {
    const html = renderToStaticMarkup(
      createElement(
        I18nProvider,
        null,
        createElement(LanguageSwitcher, { variant: "toggle" }),
      ),
    );

    expect(html.match(/<button/g)).toHaveLength(1);
    expect(html).toContain("language-toggle");
    expect(html).toContain(">VI</button>");
    expect(html).not.toContain("language-switcher");
  });

  it("flips VI to EN and EN to VI", () => {
    expect(getNextLocale("vi")).toBe("en");
    expect(getNextLocale("en")).toBe("vi");
  });
});
