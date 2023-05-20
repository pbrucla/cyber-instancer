import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import Home from "./home";
import {BrowserRouter} from "react-router-dom";
import {Routes, Route} from "react-router-dom";
import {Link} from "react-router-dom";
import Challs from "./challs";
import Profile from "./profile";
import Register from "./register";

const root = ReactDOM.createRoot(document.getElementById("root")!);
root.render(
    <React.StrictMode>
        <BrowserRouter>
            <nav>
                <div>
                    <Link to="/">Home</Link>
                    <Link to="challs">Challenges</Link>
                    <Link to="profile">Profile</Link>
                    <Link to="register">Register</Link>
                </div>
            </nav>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/challs" element={<Challs />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/register" element={<Register />} />
            </Routes>
        </BrowserRouter>
    </React.StrictMode>
);
