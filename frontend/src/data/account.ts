import {useGlobalContext} from "../index";

const useAccountManagement = () => {
    const {setIsLoggedIn} = useGlobalContext();

    function getAccountToken(): string | null {
        return localStorage.getItem("auth_token");
    }

    function setAccountToken(token: string | null): void {
        if (token === null) {
            setIsLoggedIn(false);
            localStorage.removeItem("auth_token");
        } else {
            setIsLoggedIn(true);
            localStorage.setItem("auth_token", token);
            console.log("hi2");
        }
    }

    async function validateAccountToken(): Promise<boolean> {
        return (await getAccountData()) !== null;
    }

    async function getAccountData() {
        const token = getAccountToken();
        if (token === null) {
            setIsLoggedIn(false);
            return null;
        }
        const res = await fetch("/api/accounts/profile", {
            headers: {Authorization: `Bearer ${token}`},
        });
        if (res.status !== 200) {
            setIsLoggedIn(false);
            setAccountToken(null);
            return null;
        }
        console.log("hi");
        setIsLoggedIn(true);
        return await res.json();
    }

    return {getAccountData, validateAccountToken, setAccountToken, getAccountToken};
};

export default useAccountManagement;
