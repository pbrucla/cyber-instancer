export function getAccountToken() {
    return localStorage.getItem("auth_token");
}

export function setAccountToken(token: string) {
    localStorage.setItem("auth_token", token);
}

export function validateAccountToken() {
    const token = getAccountToken();
    if (token === null) {
        return false;
    }
    fetch("/api/accounts/profile", {
        headers: {Authentication: `Bearer ${token}`},
    })
        .then(() => {
            return true;
        })
        .catch(() => {
            localStorage.removeItem("auth_token");
            return false;
        });
}
