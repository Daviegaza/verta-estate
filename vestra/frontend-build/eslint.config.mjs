import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // Downgraded from error to warn while ~400 any-typed usages are
      // incrementally replaced with proper generics across the codebase.
      "@typescript-eslint/no-explicit-any": "warn",
      // Setting state in effects is common for data-fetching patterns
      // and not always a bug.
      "react-hooks/set-state-in-effect": "warn",
      // Using <a> links can be intentional for external URLs or
      // same-page anchors.
      "@next/next/no-html-link-for-pages": "warn",
    },
  },
]);

export default eslintConfig;
