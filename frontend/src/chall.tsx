import "./styles/index.css";
import "./styles/chall.css";
import {useState, useEffect} from "react";
import {useParams, useSearchParams} from "react-router-dom";
import {ReactComponent as Timer} from "./images/timer.svg";
import {ReactComponent as Stop} from "./images/stop.svg";

import {
    SingleChallengeType,
    ChallengeInfoType,
    ChallengeDeploymentType,
    DeploymentType,
    MessageType,
} from "./util/types.ts";
import {prettyTime, getCategories, getTags, isDeployed} from "./util/utility.ts";
import useAccountManagement from "./util/account";
import {useNavigate} from "react-router-dom";

function createLink(host: string) {
    let output: string = host;
    if (!output.startsWith("https://")) {
        output = "https://" + output;
    }
    return (
        <a href={output} className="chall-link" target="_blank" rel="noreferrer noopener">
            {output}
        </a>
    );
}

const Chall = () => {
    /* Redirect if not logged in */
    const {accountToken} = useAccountManagement();
    const [searchParams, setSearchParams] = useSearchParams();
    const loginToken = searchParams.get("token");
    const navigate = useNavigate();

    const {ID} = useParams() as {ID: string};

    /* Load challenge */
    const [chall, setChall] = useState<ChallengeInfoType | undefined | null>(undefined);
    const [deployment, setDeployment] = useState<DeploymentType | undefined>();
    const [deployed, setDeployed] = useState<boolean>(false);
    const [timer, setTimer] = useState<number>(-100);

    useEffect(() => {
        function loggedOutRedirect() {
            if (loginToken === null) {
                console.debug("Redirected w/o token");
                navigate("/login");
            } else {
                console.debug("Redirected with token");
                navigate(`/login?token=${encodeURIComponent(loginToken)}&chall=${encodeURIComponent(ID)}`);
            }
        }
        if (accountToken === null) {
            loggedOutRedirect();
            return;
        }
        if (loginToken) {
            setSearchParams("");
        }
        if (timer <= 0) {
            fetch("/api/challenge/" + ID, {
                headers: {Authorization: `Bearer ${accountToken}`},
            })
                .then((res) => {
                    if (res.status === 404) {
                        setChall(null);
                        console.debug("Challenge not found");
                        return;
                    }
                    return res.json();
                })
                .then((challenge: SingleChallengeType) => {
                    if (challenge.status === "ok") {
                        setChall(challenge.challenge_info);
                        fetch("/api/challenge/" + ID + "/deployment", {
                            headers: {Authorization: `Bearer ${accountToken}`},
                        })
                            .then((res) => res.json())
                            .then((challengeDeployment: ChallengeDeploymentType) => {
                                if (challengeDeployment.status === "ok") {
                                    setDeployment(challengeDeployment.deployment);
                                } else {
                                    loggedOutRedirect();
                                }
                            })
                            .catch((err) => console.debug(err));
                    } else {
                        console.debug("Failed to get chall status");
                        loggedOutRedirect();
                    }
                })
                .catch((err) => console.debug(err));
        }
    }, [navigate, timer, ID, accountToken, loginToken, setSearchParams]);

    let challInfo;
    let buttons;

    /* Deploy challenge */
    const [isShaking, setIsShaking] = useState<boolean>(false);
    const [disableButton, setDisableButton] = useState<boolean>(false);

    function deployChallenge() {
        setIsShaking(false);
        if (disableButton) return;
        setDisableButton(true);
        fetch("/api/challenge/" + ID + "/deploy", {
            headers: {Authorization: `Bearer ${accountToken as string}`},
            method: "POST",
        })
            .then((res) => res.json())
            .then((challengeDeployment: ChallengeDeploymentType) => {
                if (challengeDeployment.status === "ok") {
                    setDeployment(challengeDeployment.deployment);
                    setErrorMsg(null);
                } else if (challengeDeployment.status === "temporarily_unavailable") {
                    console.error("Deployment error");
                    setIsShaking(true);
                    setErrorMsg("Challenge temporarily unavailable. Please wait a few moments and try again.");
                } else if (challengeDeployment.status === "missing_authorization") {
                    navigate("/login");
                } else {
                    console.error("An unexpected API response was received");
                }
                setDisableButton(false);
            })
            .catch((err) => {
                console.error(err);
                setDisableButton(false);
            });
    }

    useEffect(() => {
        setDeployed(isDeployed(deployment));
    }, [deployment]);

    /* Error messages */
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    /* Terminate challenge */
    function terminateChallenge() {
        if (disableButton) return;
        setDisableButton(true);
        fetch("/api/challenge/" + ID + "/deployment", {
            headers: {Authorization: `Bearer ${accountToken as string}`},
            method: "DELETE",
        })
            .then((res) => res.json())
            .then((status: MessageType) => {
                if (status.status === "ok") {
                    console.debug(status.msg);
                    setDeployment(undefined);
                } else {
                    console.error("error");
                    console.error(status);
                }
                setDisableButton(false);
            })
            .catch((err) => console.debug(err));
    }

    /* Timer */
    useEffect(() => {
        let interval = 0;

        if (deployed) {
            if (timer === -100 && deployment) {
                setTimer(Math.floor(deployment.expiration - Date.now() / 1000));
            } else if (timer < 0) {
                setDeployed(false);
            } else {
                interval = setInterval(() => {
                    setTimer((prevTimer) => prevTimer - 1);
                }, 1000);
            }
        } else if (!deployed) {
            clearInterval(interval);
            setTimer(-100);
        }
        return () => clearInterval(interval);
    }, [deployed, deployment, timer]);

    /* hosts and ports */
    const [ports, setPorts] = useState<(string | JSX.Element)[]>([]);

    useEffect(() => {
        if (deployed && deployment) {
            const outPorts: (string | JSX.Element)[] = [];
            const portmap = deployment.port_mappings;
            Object.keys(portmap).forEach((key) => {
                if (typeof portmap[key] === "string") {
                    outPorts.push(createLink(portmap[key] as string));
                } else {
                    outPorts.push("nc " + deployment.host + " " + (portmap[key] as string));
                }
            });
            setPorts(outPorts);
        }
    }, [deployment, deployed]);

    /* Display information */
    if (chall === null) {
        challInfo = <h1 style={{color: "#d0d0d0"}}>ERROR: CHALLENGE NOT FOUND</h1>;
    } else if (chall === undefined) {
        challInfo = <h1 style={{color: "#d0d0d0"}}>Loading...</h1>;
    } else {
        const cat = getCategories(chall);
        const title = chall.name.toUpperCase();
        const author = chall.author;
        const description = chall.description;
        const tags = getTags(chall);
        const newTags: string[] = [];

        for (let i = 0; i < tags.length; i++) {
            newTags.push("#".concat(tags[i].replaceAll(" ", "_").concat(" ").toString()));
        }

        challInfo = (
            <>
                <div style={{position: "relative", width: "90%"}}>
                    <div style={{overflowWrap: "break-word", color: "#d0d0d0", fontSize: "30px"}}>{cat}</div>
                    <br></br>
                    <div style={{overflowWrap: "break-word", color: "#ffffff", fontSize: "45px", fontWeight: "bold"}}>
                        {title.toUpperCase()}
                    </div>
                    <br></br>
                    <div style={{overflowWrap: "break-word", color: "#ff8c4c", fontSize: "30px"}}>{newTags}</div>
                    <br></br>
                    <div style={{overflowWrap: "break-word", color: "#d0d0d0", fontSize: "25px"}}>
                        <b>AUTHOR:</b> {author}
                    </div>
                    <br></br>
                    <div style={{overflowWrap: "break-word", color: "#f0f0f0", fontSize: "25px"}}>
                        <b>Description:</b>
                    </div>
                    <br></br>
                    <div style={{overflowWrap: "break-word", color: "#f0f0f0", fontSize: "20px"}}>{description}</div>
                    <br></br>
                </div>
            </>
        );

        if (deployed && deployment) {
            buttons = (
                <div className="deployment-info">
                    {chall.is_shared ? (
                        <>
                            <button className="deploy ON shared">
                                <Timer className="buttonsvg l" />
                                <span style={{marginLeft: "0", marginRight: "4rem"}}>{prettyTime(timer)}</span>
                            </button>
                            <div className="IP-port-box"> SHARED CHALLENGE </div>
                        </>
                    ) : (
                        <button className="deploy ON" onClick={terminateChallenge} disabled={disableButton}>
                            <Timer className="buttonsvg l" />
                            <span style={{marginLeft: "0"}}>{prettyTime(timer)}</span>
                            <Stop className="buttonsvg r" />
                        </button>
                    )}
                    {Date.now() / 1000 > deployment.start_delay ? (
                        ports.map((p: string | JSX.Element) => (
                            <div className="IP-port-box" key={p as string}>
                                {p}
                            </div>
                        ))
                    ) : (
                        <div className="IP-port-box" key="loading">
                            loading challenge information...
                        </div>
                    )}
                </div>
            );
        } else {
            buttons = (
                <>
                    <button
                        className={"deploy OFF" + (isShaking ? " shake-animation" : "")}
                        onClick={deployChallenge}
                        disabled={disableButton}
                    >
                        DEPLOY NOW
                    </button>
                    {errorMsg && <div className="errorMsg">{errorMsg}</div>}
                </>
            );
        }
    }

    return (
        <div className="content-div">
            {challInfo}
            {buttons}
        </div>
    );
};
export default Chall;
