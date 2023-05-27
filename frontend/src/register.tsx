import "./styles/index.css";
import "./styles/info-box.css";
import {FormEvent, useState} from "react";
import * as accounts from "./data/account";
import {useNavigate} from "react-router-dom";

const Register = () => {
    const navigate = useNavigate();

    const [formStatus, setFormStatus] = useState("");

    const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
        // Prevent the browser from reloading the page
        e.preventDefault();

        // Read the form data
        const form = e.currentTarget;
        const formData = new FormData(form);

        await fetch("/api/accounts/register", {
            method: "POST",
            body: formData,
        })
            .then((res) => {
                if (res.status === 200) {
                    console.log("success!");
                    res.json()
                        .then((data) => data.token)
                        .then((token) => accounts.setAccountToken(token))
                        .then(() => navigate("/challs"))
                        .catch(() => console.log("An unexpected error occurred"));
                } else {
                    console.log("failed");
                    res.json()
                        .then((data) => data.msg)
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
            <div className="Profile-Register-div">
                <div className="Profile-Register-div-inner">
                    <h1 className="Profile-Register-heading"> REGISTER </h1>
                    <form className="container" method="post" onSubmit={handleSubmit}>
                        <div className="row">
                            <div className="column" style={{borderRadius: "5px 0 0 0"}}>
                                USERNAME
                            </div>
                            <input type="text" name="username" className="column" style={{borderRadius: "0 5px 0 0"}} />
                        </div>
                        <div className="row">
                            <div className="column" style={{borderRadius: "0 0 0 5px"}}>
                                EMAIL
                            </div>
                            <input type="text" name="email" className="column" style={{borderRadius: "0 0 5px 0"}} />
                        </div>
                        <div className="row">
                            <button type="submit">Register</button>
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

export default Register;
