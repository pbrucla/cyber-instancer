import useLocalStorageState from "use-local-storage-state";

const useAccountManagement = () => {
    const [accountToken, setAccountToken, {removeItem: unsetAccountToken}] = useLocalStorageState<string | null>(
        "auth_token",
        {
            defaultValue: null,
        }
    );

    async function validateAccountToken(): Promise<boolean> {
        if (accountToken === null) {
            return false;
        }
        const res = await fetch("/api/accounts/profile", {
            headers: {Authorization: `Bearer ${accountToken}`},
        });
        return res.status === 200;
    }

    return {validateAccountToken, setAccountToken, accountToken, unsetAccountToken};
};

export default useAccountManagement;
