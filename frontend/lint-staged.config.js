module.exports = {
    "src/**/*.ts?(x)": [
        () => "tsc --noEmit",
        "eslint --report-unused-disable-directives --max-warnings 0",
        "prettier --write",
    ],
    "!(src/**/*.ts?(x))": "prettier --write --ignore-unknown",
};
