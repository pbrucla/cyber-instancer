module.exports = {
    extends: [
        "eslint:recommended",
        "plugin:@typescript-eslint/recommended",
        "plugin:@typescript-eslint/recommended-requiring-type-checking",
        "plugin:react/recommended",
        "plugin:react/jsx-runtime",
        "react-app",
        "react-app/jest",
        "prettier",
    ],
    plugins: ["@typescript-eslint", "react"],
    parser: "@typescript-eslint/parser",
    parserOptions: {
        project: ["./tsconfig.json", "./tsconfig.eslint.json", "./tsconfig.node.json"],
        tsconfigRootDir: __dirname,
    },
    reportUnusedDisableDirectives: true,
    root: true,
};
