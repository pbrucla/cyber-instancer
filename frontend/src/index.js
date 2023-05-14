import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";
import reportWebVitals from "./reportWebVitals";
import {BrowserRouter} from "react-router-dom";
import {Routes, Route} from "react-router-dom";
import {Link} from "react-router-dom";
import Challs from "./challs.js";
import Profile from "./profile.js";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
    <React.StrictMode>
        <BrowserRouter>
            <h1>ACM Cyber</h1>
            <nav>
                <div>
                    <Link to="/">Home</Link>
                    <Link to="challs">Challenges</Link>
                    <Link to="profile">Profile</Link>
                </div>
            </nav>
            <Routes>
                <Route path="/" element={<App />} />
                <Route path="/challs" element={<Challs />} />
                <Route path="/profile" element={<Profile />} />
            </Routes>
        </BrowserRouter>
    </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
