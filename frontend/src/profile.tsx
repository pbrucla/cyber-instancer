import "./styles/index.css";
import "./styles/info-box.css";
import useAccountManagement from "./util/account";
import {useEffect, useState} from "react";
import {useNavigate} from "react-router-dom";
import {ProfileType, MessageType} from "./util/types.ts";

const Profile = () => {
    const navigate = useNavigate();
    const {accountToken} = useAccountManagement();

    const [username, setUsername] = useState("Loading...");
    const [email, setEmail] = useState("Loading...");
    const [loginURL, setLoginURL] = useState("Loading...");
    const [isShaking, setIsShaking] = useState([false, false]);
    const [success, setSuccess] = useState([false, false]);
    const [errorMsg, setErrorMsg] = useState("");

    useEffect(() => {
        if (accountToken === null) {
            navigate("/login");
            return;
        }
        fetch("/api/accounts/profile", {
            headers: {Authorization: `Bearer ${accountToken}`},
        })
            .then((res) => {
                if (res.status !== 200) {
                    navigate("/login");
                    return;
                }
                return res.json();
            })
            .then((profileData: ProfileType) => {
                if (profileData === null) {
                    navigate("/login");
                    return;
                } else {
                    setUsername(profileData.username ? profileData.username : "");
                    setEmail(profileData.email ? profileData.email : "");
                    setLoginURL(profileData.login_url);
                }
            })
            .catch((err) => console.debug(err));
    }, [navigate, accountToken]);

    function updateProfile(updateUsername: boolean, updateEmail: boolean) {
        setIsShaking([false, false]);
        setSuccess([false, false]);
        if (accountToken === null) {
            navigate("/login");
            return null;
        }
        fetch("/api/accounts/profile", {
            method: "PATCH",
            headers: {Authorization: `Bearer ${accountToken}`, "Content-Type": "application/x-www-form-urlencoded"},
            body:
                (updateUsername ? `username=${encodeURIComponent(username)}` : ``) +
                (updateUsername && updateEmail ? `&` : ``) +
                (updateEmail ? `email=${encodeURIComponent(email)}` : ``),
        })
            .then((res) => {
                if (res.status !== 200) {
                    setIsShaking([updateUsername, updateEmail]);
                    res.json()
                        .then((body: MessageType) => setErrorMsg(body.msg))
                        .catch(() => setErrorMsg("An unexpected error occurred"));
                    return null;
                } else {
                    setErrorMsg("");
                    setSuccess([updateUsername, updateEmail]);
                    setTimeout(() => {
                        setSuccess([false, false]);
                    }, 3000);
                    return res.json();
                }
            })
            .then((responseMessage: MessageType) => {
                console.debug(responseMessage.msg);
            })
            .catch((err) => console.debug(err));
    }

    function handleInputChange(event: React.ChangeEvent<HTMLInputElement>, setter: (arg: string) => void) {
        setter(event.target.value);
    }

    return (
        <>
            <div className="Profile-Register-div">
                <div className="Profile-Register-div-inner">
                    <h1 className="Profile-Register-heading"> PROFILE </h1>
                    <div className="container">
                        <div className="row">
                            <div className="column" style={{borderRadius: "0.7rem 0 0 0"}}>
                                USERNAME
                            </div>
                            <input
                                className="column column1"
                                style={{wordBreak: "break-all", whiteSpace: "normal"}}
                                type="text"
                                value={username}
                                onChange={(event) => handleInputChange(event, setUsername)}
                            />
                            <button
                                className={"column column1 " + (isShaking[0] ? " shake-animation" : "")}
                                onClick={() => {
                                    updateProfile(true, false);
                                }}
                                style={{borderRadius: "0 0.7rem 0 0"}}
                            >
                                UPDATE USERNAME
                            </button>
                        </div>
                        <div className="row">
                            <div className="column">REGISTERED EMAIL</div>
                            <input
                                className="column column1"
                                style={{wordBreak: "break-all", whiteSpace: "normal"}}
                                type="text"
                                value={email}
                                onChange={(event) => handleInputChange(event, setEmail)}
                            />
                            <button
                                className={"column column1 " + (isShaking[1] ? " shake-animation" : "")}
                                onClick={() => {
                                    updateProfile(false, true);
                                }}
                            >
                                UPDATE EMAIL
                            </button>
                        </div>
                        <div className="row">
                            <div className="column" style={{borderRadius: "0 0 0 0.7rem"}}>
                                LOGIN URL
                            </div>
                            <div
                                className="column column2"
                                style={{
                                    borderRadius: "0 0 0.7rem 0",
                                    wordBreak: "break-all",
                                    whiteSpace: "normal",
                                }}
                            >
                                {loginURL}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            {(success[0] || success[1]) && (
                <div className="centered-message">
                    <span className="dot"></span>Updated {success[0] ? "username" : "email"} successfully!
                </div>
            )}
            <div className="centered-message">{errorMsg && "Error: " + errorMsg}</div>
        </>
    );
};

export default Profile;
