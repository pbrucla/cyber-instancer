import "./styles/index.css";
import React from "react";
import ReactDOM from "react-dom/client";
import {BrowserRouter} from "react-router-dom";
import {Routes, Route} from "react-router-dom";
import {Link, useNavigate} from "react-router-dom";

import App from "./home";
import Challs from "./challs";
import Profile from "./profile";
import Register from "./register";
import Chall from "./chall";
import Login from "./login";
import config from "./util/config";
import useAccountManagement from "./util/account";
import {ReactComponent as HomeBtn} from "./images/home.svg";

function NavComponents({accountToken}: {accountToken: string | null}) {
    const {setAccountToken} = useAccountManagement();
    const navigate = useNavigate();

    const logout = () => {
        if (accountToken === null) {
            navigate("/");
            return;
        }

        fetch("/api/accounts/logout", {
            method: "POST",
            headers: {
                Authorization: `Bearer ${accountToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                token: accountToken,
            }),
        })
            .then((res) => {
                if (res.status === 200) {
                    setAccountToken(null);
                    if (config.rctf_mode && config.rctf_url !== null) {
                        window.location.href = config.rctf_url;
                    } else {
                        navigate("/");
                    }
                }
            })
            .catch((err) => {
                console.log(err);
            });
    };

    if (accountToken !== null) {
        return (
            <>
                <button className="button right" onClick={() => logout()}>
                    LOG OUT
                </button>
                {!config.rctf_mode && (
                    <Link to="profile">
                        <button className="button right">PROFILE</button>
                    </Link>
                )}
                {config.rctf_mode && config.rctf_url !== null ? (
                    <a href={`${config.rctf_url}/challs`}>
                        <button className="button right">CHALLS</button>
                    </a>
                ) : (
                    <Link to="challs">
                        <button className="button right">CHALLS</button>
                    </Link>
                )}
            </>
        );
    } else {
        return (
            <>
                {!config.rctf_mode && (
                    <Link to="register">
                        <button className="button right">REGISTER</button>
                    </Link>
                )}
                {config.rctf_mode && config.rctf_url !== null && (
                    <a href={`${config.rctf_url}/register`}>
                        <button className="button right">REGISTER</button>
                    </a>
                )}

                <Link to="login">
                    <button className="button right">LOGIN</button>
                </Link>
            </>
        );
    }
}

function IndexComponent() {
    const {accountToken} = useAccountManagement();

    return (
        <React.StrictMode>
            <BrowserRouter>
                <nav>
                    <div>
                        {config.rctf_url !== null && config.rctf_mode ? (
                            <a href={config.rctf_url}>
                                <button className="homeButton">
                                    <HomeBtn className="svg" />
                                </button>
                            </a>
                        ) : (
                            <Link to="/">
                                <button className="homeButton">
                                    <HomeBtn className="svg" />
                                </button>
                            </Link>
                        )}
                        <NavComponents accountToken={accountToken} />
                    </div>
                </nav>
                <Routes>
                    <Route path="/" element={<App />} />
                    <Route path="/challs" element={<Challs />} />
                    <Route path="/profile" element={<Profile />} />
                    <Route path="/register" element={<Register />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/chall/:ID" element={<Chall />} />
                </Routes>
            </BrowserRouter>
        </React.StrictMode>
    );
}

const root = ReactDOM.createRoot(document.getElementById("root")!);
root.render(<IndexComponent />);
