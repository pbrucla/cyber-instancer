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
import useAccountManagement from "./data/account";
import {ReactComponent as HomeBtn} from "./images/home.svg";

function NavComponents({accountToken}: {accountToken: string | null}) {
    const {setAccountToken} = useAccountManagement();
    const navgiate = useNavigate();

    const logout = () => {
        setAccountToken(null);
        navgiate("/");
    };

    if (accountToken !== null) {
        return (
            <>
                <button className="button right" onClick={() => logout()}>
                    LOG OUT
                </button>
                <Link to="profile">
                    <button className="button right">PROFILE</button>
                </Link>
                <Link to="challs">
                    <button className="button right">CHALLS</button>
                </Link>
            </>
        );
    } else {
        return (
            <>
                <Link to="register">
                    <button className="button right">REGISTER</button>
                </Link>
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
                        <Link to="/">
                            <button className="homeButton">
                                <HomeBtn className="svg" />
                            </button>
                        </Link>
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
