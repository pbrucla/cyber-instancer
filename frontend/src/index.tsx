import React from "react";
import ReactDOM from "react-dom/client";
import {BrowserRouter} from "react-router-dom";
import {Routes, Route} from "react-router-dom";
import {Link} from "react-router-dom";

import App from "./home";
import Challs from "./challs";
import Profile from "./profile";
import Register from "./register";
import Chall from "./chall";

import "./styles/index.css";
import {ReactComponent as HomeBtn} from "./images/home.svg";

const root = ReactDOM.createRoot(document.getElementById("root")!);
root.render(
    <React.StrictMode>
        <BrowserRouter>   
            <nav>
                <div>
                    <Link to="challs"><button className="left"><HomeBtn className="svg"/></button></Link>
                    <Link to="profile"><button className="right">PROFILE</button></Link>
                </div>
            </nav>  
            <Routes>
                <Route path="/" element={<App />} />
                <Route path="/challs" element={<Challs />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/register" element={<Register />} />
                <Route path="/chall" element={<Chall />} />
            </Routes>
        </BrowserRouter>
    </React.StrictMode>
);