import { QuartzConfig } from "./quartz/cfg";
import * as Plugin from "./quartz/plugins";

/**
 * Конфигурация Quartz 4.5+
 */
const config: QuartzConfig = {
  configuration: {
    pageTitle: "Архив",
    pageTitleSuffix: "",
    enableSPA: true,
    enablePopovers: true,
    analytics: null,
    locale: "ru-RU",
    baseUrl: "notes.vlsu-hub.org",
    ignorePatterns: ["private", "templates", ".obsidian", "**/_*.md"],
    defaultDateType: "created",

    theme: {
      fontOrigin: "googleFonts",
      cdnCaching: true,
      typography: {
        header: "Inter",
        body: "Inter",
        code: "JetBrains Mono",
      },
      colors: {
        lightMode: {
          light: "#ffffff",
          lightgray: "#e9ecef",
          gray: "#adb5bd",
          darkgray: "#343a40",
          dark: "#181a1f",
          secondary: "#2563eb",
          tertiary: "#60a5fa",
          highlight: "rgba(37, 99, 235, 0.1)",
          textHighlight: "#fef08a",
        },
        darkMode: {
          light: "#111317",
          lightgray: "#22262e",
          gray: "#6b7280",
          darkgray: "#d1d5db",
          dark: "#f3f4f6",
          secondary: "#60a5fa",
          tertiary: "#93c5fd",
          highlight: "rgba(96, 165, 250, 0.12)",
          textHighlight: "#854d0e88",
        },
      },
    },
  },
  plugins: {
    transformers: [
      Plugin.FrontMatter(),
      Plugin.CreatedModifiedDate({
        priority: ["frontmatter", "filesystem"],
      }),
      Plugin.SyntaxHighlighting({
        theme: {
          light: "github-light",
          dark: "github-dark",
        },
        keepBackground: false,
      }),
      Plugin.ObsidianFlavoredMarkdown({ enableInHtmlEmbed: false }),
      Plugin.GitHubFlavoredMarkdown(),
      Plugin.TableOfContents(),
      Plugin.CrawlLinks({ markdownLinkResolution: "shortest" }),
      Plugin.Description(),
      Plugin.Latex({ renderEngine: "mathjax" }),
    ],
    filters: [Plugin.RemoveDrafts()],
    emitters: [
      Plugin.AliasRedirects(),
      Plugin.ComponentResources(),
      Plugin.ContentPage(),
      Plugin.FolderPage({
        sort: (f1, f2) => {
          const title1 = f1.frontmatter?.title ?? f1.file!.stem;
          const title2 = f2.frontmatter?.title ?? f2.file!.stem;
          return title1.localeCompare(title2, undefined, { numeric: true });
        },
      }),
      Plugin.TagPage({
        sort: (f1, f2) => {
          const title1 = f1.frontmatter?.title ?? f1.file!.stem;
          const title2 = f2.frontmatter?.title ?? f2.file!.stem;
          return title1.localeCompare(title2, undefined, { numeric: true });
        },
      }),
      Plugin.ContentIndex({
        enableSiteMap: true,
        enableRSS: true,
      }),
      Plugin.Assets(),
      Plugin.Static(),
      Plugin.NotFoundPage(),
    ],
  },
};

export default config;
