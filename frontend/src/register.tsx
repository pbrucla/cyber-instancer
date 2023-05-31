import "./styles/index.css";
import "./styles/info-box.css";
import {FormEvent, useState, useEffect} from "react";
import useAccountManagement from "./data/account";
import {useNavigate} from "react-router-dom";

const Register = () => {
    const navigate = useNavigate();

    const [formStatus, setFormStatus] = useState("");
    const {setAccountToken, validateAccountToken} = useAccountManagement();

    /* Redirect if logged in */
    useEffect(() => {
        const checkLoggedIn = async () => {
            if (await validateAccountToken()) {
                navigate("/challs");
            }
        };
        checkLoggedIn().catch(console.error);
    }, [navigate, validateAccountToken]);

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
                        .then((data: {token: string}) => data.token)
                        .then((token) => setAccountToken(token))
                        .then(() => navigate("/challs"))
                        .catch(() => console.log("An unexpected error occurred"));
                } else {
                    console.log("failed");
                    res.json()
                        .then((data: {msg: string}) => data.msg)
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
                    <form
                        className="container"
                        method="post"
                        onSubmit={(e) => {
                            void handleSubmit(e);
                        }}
                    >
                        <div className="row">
                            <div className="column" style={{borderRadius: "5px 0 0 0"}}>
                                USERNAME
                            </div>
                            <input
                                type="text"
                                className="column"
                                placeholder="Enter here..."
                                name="username"
                                style={{borderRadius: "0 5px 0 0"}}
                            />
                        </div>
                        <div className="row">
                            <div className="column" style={{borderRadius: "0 0 0 5px"}}>
                                EMAIL
                            </div>
                            <input
                                type="text"
                                className="column"
                                placeholder="Enter here..."
                                name="email"
                                style={{borderRadius: "0 0 5px 0"}}
                            />
                        </div>
                        <div className="row">
                            <button className="button" type="submit">
                                REGISTER
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

export default Register;
