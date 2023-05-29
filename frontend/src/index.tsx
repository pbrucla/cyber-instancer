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

import "./styles/index.css";
import {ReactComponent as HomeBtn} from "./images/home.svg";

import {useState, createContext, useContext} from "react";

export type GlobalContent = {
    isLoggedIn: boolean;
    setIsLoggedIn: (c: boolean) => void;
};
export const GlobalContext = createContext({
    isLoggedIn: false,
    setIsLoggedIn: (_c: boolean) => {
        return;
    },
});
export const useGlobalContext = () => useContext(GlobalContext);

function NavComponents({showLoggedIn}: {showLoggedIn: boolean}) {
    const {setAccountToken} = useAccountManagement();
    const navgiate = useNavigate();

    const logout = () => {
        setAccountToken(null);
        navgiate("/");
    };

    if (showLoggedIn === true) {
        return (
            <>
                <button className="right" onClick={() => logout()}>
                    LOG OUT
                </button>
                <Link to="profile">
                    <button className="right">PROFILE</button>
                </Link>
                <Link to="challs">
                    <button className="right">CHALLS</button>
                </Link>
            </>
        );
    } else {
        return (
            <>
                <Link to="register">
                    <button className="right">REGISTER</button>
                </Link>
                <Link to="login">
                    <button className="right">LOGIN</button>
                </Link>
            </>
        );
    }
}

function IndexComponent() {
    const {getAccountToken} = useAccountManagement();

    const [isLoggedIn, setIsLoggedIn] = useState(getAccountToken() !== null);
    return (
        <React.StrictMode>
            <GlobalContext.Provider value={{isLoggedIn, setIsLoggedIn}}>
                <BrowserRouter>
                    <nav>
                        <div>
                            <Link to="/">
                                <button className="left">
                                    <HomeBtn className="svg" />
                                </button>
                            </Link>
                            <NavComponents showLoggedIn={isLoggedIn} />
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
            </GlobalContext.Provider>
        </React.StrictMode>
    );
}

const root = ReactDOM.createRoot(document.getElementById("root")!);
root.render(<IndexComponent />);
