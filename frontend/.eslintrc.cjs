module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
  plugins: ["@typescript-eslint", "react-hooks"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  ignorePatterns: ["dist/", "coverage/", "node_modules/", "src/vite-env.d.ts"],
  rules: {
    "spaced-comment": ["error", "always"],
    "@typescript-eslint/consistent-type-imports": ["error", { prefer: "type-imports" }],
  },
};
