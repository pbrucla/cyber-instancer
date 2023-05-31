import "./styles/index.css";
import "./styles/info-box.css";
import useAccountManagement from "./data/account";
import {useEffect, useState} from "react";
import {useNavigate} from "react-router-dom";

const Profile = () => {
    const navigate = useNavigate();
    const {getAccountData} = useAccountManagement();

    const [username, setUsername] = useState("Loading...");
    const [email, setEmail] = useState("Loading...");
    const [loginURL, setLoginURL] = useState("Loading...");

    useEffect(() => {
        const updateProfileData = async () => {
            const profileData = (await getAccountData()) as {username: string; email: string; login_url: string};
            if (profileData === null) {
                navigate("/login");
            } else {
                setUsername(profileData.username);
                setEmail(profileData.email);
                setLoginURL(profileData.login_url);
            }
        };

        updateProfileData().catch(console.error);
    }, [getAccountData, navigate]);

    return (
        <>
            <div className="Profile-Register-div">
                <div className="Profile-Register-div-inner">
                    <h1 className="Profile-Register-heading"> PROFILE </h1>
                    <div className="container">
                        <div className="row">
                            <div className="column" style={{borderRadius: "5px 0 0 0"}}>
                                USERNAME
                            </div>
                            <div
                                className="column"
                                style={{borderRadius: "0 5px 0 0", wordBreak: "break-all", whiteSpace: "normal"}}
                            >
                                {username}
                            </div>
                        </div>
                        <div className="row">
                            <div className="column" >
                                REGISTERED EMAIL
                            </div>
                            <div
                                className="column"
                                style={{wordBreak: "break-all", whiteSpace: "normal"}}
                            >
                                {email}
                            </div>
                        </div>
                        <div className="row">
                            <div className="column" style={{borderRadius: "0 0 0 5px"}}>
                                LOGIN URL
                            </div>
                            <div
                                className="column"
                                style={{borderRadius: "0 0 5px 0", wordBreak: "break-all", whiteSpace: "normal"}}
                            >
                                {loginURL}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default Profile;
