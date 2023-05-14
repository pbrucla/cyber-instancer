module.exports = {
    "src/**/*.ts?(x)": () => "tsc --noEmit",
    "vite.config.ts": () => "tsc -p tsconfig.node.json --noEmit",
    "**/*.[tj]s?(x)": "eslint --max-warnings 0",
    "*": "prettier --check --ignore-unknown",
};
