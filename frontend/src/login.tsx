import "./styles/index.css";
import "./styles/info-box.css";
import {FormEvent, useState, useEffect, useCallback} from "react";
import useAccountManagement from "./util/account";
import {useNavigate, useSearchParams} from "react-router-dom";

const Login = () => {
    const navigate = useNavigate();

    const {setAccountToken, validateAccountToken} = useAccountManagement();

    const [formStatus, setFormStatus] = useState("");
    const [token, setToken] = useState("");
    const [searchParams] = useSearchParams();
    const [loginAs, setLoginAs] = useState("");

    useEffect(() => {
        const token = searchParams.get("token");
        if (token !== null) {
            setToken(token);
            fetch(`/api/accounts/preview?login_token=${encodeURIComponent(token)}`)
                .then((res) => {
                    if (res.status !== 200) throw Error("Invalid Token");
                    else return res;
                })
                .then((res) => res.json())
                .then((resJson) => {
                    if ((resJson as {team_name: string}).team_name !== null) {
                        setLoginAs((resJson as {team_name: string}).team_name);
                    } else {
                        console.debug("Token does not contain team information");
                    }
                })
                .catch(() => {
                    console.error("Invalid token");
                });
        }
    }, [searchParams, navigate]);

    const loggedInRedirect = useCallback(() => {
        const challRed = searchParams.get("chall");
        // Validate chall to prevent arbitrary redirects
        const validChallName = new RegExp("^[0-9a-zA-Z-]+$");

        if (challRed === null) {
            navigate("/profile");
        } else {
            if (!validChallName.test(challRed)) {
                navigate("/profile");
            } else {
                navigate(`/chall/${encodeURIComponent(challRed)}/`);
            }
        }
    }, [navigate, searchParams]);

    useEffect(() => {
        /* Redirect if logged in */
        const checkLoggedIn = async () => {
            if (await validateAccountToken()) {
                loggedInRedirect();
            } else {
                setAccountToken(null);
            }
        };
        checkLoggedIn().catch(console.error);
    }, [validateAccountToken, setAccountToken, navigate, loggedInRedirect]);

    const attemptLogin = (formData: FormData) => {
        fetch("/api/accounts/login", {
            method: "POST",
            body: formData,
        })
            .then((res) => {
                if (res.status === 200) {
                    console.debug("login success!");
                    res.json()
                        .then((data) => (data as {token: string}).token)
                        .then((token) => {
                            setAccountToken(token);
                        })
                        .then(() => loggedInRedirect())
                        .catch(() => console.error("An unexpected error occurred"));
                } else {
                    console.error("failed to login");
                    res.json()
                        .then((data) => (data as {msg: string}).msg)
                        .then((errmsg) => setFormStatus(errmsg))
                        .catch(() => console.error("An unexpected error occurred"));
                }
            })
            .catch(() => {
                console.error("An unexpected error occurred");
            });
    };

    const onLoginSubmit = () => {
        const formData = new FormData();
        formData.append("login_token", token);
        attemptLogin(formData);
    };

    const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
        // Prevent the browser from reloading the page
        e.preventDefault();

        // Read the form data
        const form = e.currentTarget;
        const formData = new FormData(form);
        attemptLogin(formData);
    };

    return (
        <>
            <div className="Profile-Login-div">
                <div className="Profile-Login-div-inner">
                    {loginAs === "" ? (
                        <>
                            <h1 className="Profile-Login-heading"> LOGIN </h1>
                            <form
                                className="container"
                                method="post"
                                onSubmit={(e) => {
                                    void handleSubmit(e);
                                }}
                            >
                                <div className="row">
                                    <div className="column" style={{borderRadius: "0.7rem 0 0 0.7rem"}}>
                                        TOKEN
                                    </div>
                                    <input
                                        type="text"
                                        placeholder="Enter here..."
                                        name="login_token"
                                        className="column column2"
                                        defaultValue={token}
                                        style={{borderRadius: "0 0.7rem 0.7rem 0"}}
                                    />
                                </div>
                                <div className="row">
                                    <button type="submit" className="button">
                                        SUBMIT
                                    </button>
                                </div>
                                <div className="status">
                                    <h4>{formStatus}</h4>
                                </div>
                            </form>
                        </>
                    ) : (
                        <>
                            <h1 className="Profile-Login-heading"> Login as {loginAs}?</h1>
                            <div className="Login-Button-Box">
                                <button className="Login-Button" onClick={onLoginSubmit}>
                                    Login
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </>
    );
};

export default Login;
