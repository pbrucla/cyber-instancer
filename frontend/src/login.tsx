import "./styles/index.css";
import "./styles/info-box.css";
import {FormEvent, useState, useEffect} from "react";
import useAccountManagement from "./data/account";
import {useNavigate, useSearchParams} from "react-router-dom";

const Login = () => {
    const navigate = useNavigate();

    const {setAccountToken, validateAccountToken} = useAccountManagement();

    const [formStatus, setFormStatus] = useState("");
    const [token, setToken] = useState("");
    const [searchParams] = useSearchParams();

    useEffect(() => {
        const token = searchParams.get("token");
        if (token !== null) {
            setToken(token);
        }

        /* Redirect if logged in */
        const checkLoggedIn = async () => {
            if (await validateAccountToken()) {
                navigate("/challs");
            }
        };
        checkLoggedIn().catch(console.error);
    }, [searchParams, navigate, validateAccountToken]);

    const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
        // Prevent the browser from reloading the page
        e.preventDefault();

        // Read the form data
        const form = e.currentTarget;
        const formData = new FormData(form);

        await fetch("/api/accounts/login", {
            method: "POST",
            body: formData,
        })
            .then((res) => {
                if (res.status === 200) {
                    console.log("success!");
                    res.json()
                        .then((data) => (data as {token: string}).token)
                        .then((token) => setAccountToken(token))
                        .then(() => navigate("/challs"))
                        .catch(() => console.log("An unexpected error occurred"));
                } else {
                    console.log("failed");
                    res.json()
                        .then((data) => (data as {msg: string}).msg)
                        .then((errmsg) => setFormStatus(errmsg))
                        .catch(() => console.log("An unexpected error occurred"));
                }
            })
            .catch(() => {
                console.log("An unexpected error occurred");
            });
    };

    return (
        <>
            <div className="Profile-Login-div">
                <div className="Profile-Login-div-inner">
                    <h1 className="Profile-Login-heading"> LOGIN </h1>
                    <form
                        className="container"
                        method="post"
                        onSubmit={(e) => {
                            void handleSubmit(e);
                        }}
                    >
                        <div className="row">
                            <div className="column" style={{borderRadius: "5px 0 0 0"}}>
                                TOKEN
                            </div>
                            <input
                                type="text"
                                name="login_token"
                                className="column"
                                defaultValue={token}
                                style={{borderRadius: "0 5px 0 0"}}
                            />
                        </div>
                        <div className="row">
                            <button type="submit" className="button">
                                Submit
                            </button>
                        </div>
                        <div className="status">
                            <h4>{formStatus}</h4>
                        </div>
                    </form>
                </div>
            </div>
        </>
    );
};

export default Login;
