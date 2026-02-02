import "./styles/index.css";
import "./styles/chall.css";
import {useState, useEffect, useRef} from "react";
import {useNavigate, useParams, useSearchParams} from "react-router-dom";
import {ReactComponent as Timer} from "./images/timer.svg";
import {ReactComponent as Stop} from "./images/stop.svg";
import ReactMarkdown from "react-markdown";

import {
    SingleChallengeType,
    ChallengeInfoType,
    ChallengeDeploymentType,
    DeploymentType,
    MessageType,
} from "./util/types.ts";
import {prettyTime, getCategories, getTags, isDeployed} from "./util/utility.ts";
import useAccountManagement from "./util/account";

import config from "./util/config";
import ReCaptcha from "react-google-recaptcha";

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

    const captchaRef = useRef<ReCaptcha>(null);

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
                                    if (loginToken) {
                                        setSearchParams("");
                                    }
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

    /* Deploy and extend challenge */
    const [isShaking, setIsShaking] = useState<boolean[]>([false, false]);
    const [disableButton, setDisableButton] = useState<boolean[]>([false, false]);
    const [extended, setExtended] = useState<boolean>(false);

    function deployChallenge(index: number) {
        updateArr(index, isShaking, setIsShaking, false);
        if (disableButton[index]) return;
        updateArr(index, disableButton, setDisableButton, true);

        // Function to make the API call
        const makeDeployRequest = (captcha_token: string | null = null) => {
            const requestBody: {captcha_token?: string} = {};
            if (captcha_token) {
                requestBody.captcha_token = captcha_token;
            }

            return fetch("/api/challenge/" + ID + "/deploy", {
                headers: {
                    Authorization: `Bearer ${accountToken as string}`,
                    "Content-Type": "application/json",
                },
                method: "POST",
                body: JSON.stringify(requestBody),
            })
                .then((res) => res.json())
                .then((challengeDeployment: ChallengeDeploymentType) => {
                    if (challengeDeployment.status === "ok") {
                        setDeployment(challengeDeployment.deployment);
                        setErrorMsg(null);
                        if (index === 1) setExtended(true);
                    } else if (challengeDeployment.status === "temporarily_unavailable") {
                        console.error("Deployment error");
                        updateArr(index, isShaking, setIsShaking, true);
                        setErrorMsg("Challenge temporarily unavailable. Please wait a few moments and try again.");
                    } else if (challengeDeployment.status === "invalid_captcha_token") {
                        updateArr(index, isShaking, setIsShaking, true);
                        setErrorMsg("CAPTCHA is required");
                    } else if (
                        challengeDeployment.status === "missing_authorization" ||
                        challengeDeployment.status === "invalid_token"
                    ) {
                        navigate("/login");
                    } else {
                        console.error("An unexpected API response was received");
                    }
                    updateArr(index, disableButton, setDisableButton, false);
                    if (config.recaptcha_site_key) {
                        captchaRef.current?.reset();
                    }
                })
                .catch((err) => {
                    console.error(err);
                    updateArr(index, disableButton, setDisableButton, false);
                });
        };

        // If recaptcha is configured, execute captcha first
        if (config.recaptcha_site_key) {
            captchaRef.current
                ?.executeAsync()
                .then((captcha_token) => makeDeployRequest(captcha_token))
                .catch((err) => {
                    console.error("reCAPTCHA execution failed", err);
                    updateArr(index, disableButton, setDisableButton, false);
                    updateArr(index, isShaking, setIsShaking, true);
                    setErrorMsg("Failed to verify CAPTCHA. Please try again.");
                    captchaRef.current?.reset();
                });
        } else {
            // If recaptcha is not configured, make request directly
            makeDeployRequest().catch((err) => {
                console.error("Deploy request failed", err);
                updateArr(index, disableButton, setDisableButton, false);
                updateArr(index, isShaking, setIsShaking, true);
                setErrorMsg("Deployment failed. Please try again.");
            });
        }
    }

    function updateArr(
        index: number,
        state: boolean[],
        updateState: React.Dispatch<React.SetStateAction<boolean[]>>,
        newValue: boolean
    ) {
        const newArray = [...state];
        newArray[index] = newValue;
        updateState(newArray);
    }

    useEffect(() => {
        setDeployed(isDeployed(deployment));
    }, [deployment]);

    /* Error messages */
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    /* Terminate challenge */
    function terminateChallenge() {
        if (disableButton[0]) return;
        updateArr(0, disableButton, setDisableButton, true);
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
                updateArr(0, disableButton, setDisableButton, false);
            })
            .catch((err) => console.debug(err));
    }

    /* Timer */
    useEffect(() => {
        let interval = 0;

        if (deployed) {
            if ((timer === -100 || extended) && deployment) {
                setTimer(Math.floor(deployment.expiration - Date.now() / 1000));
                setExtended(false);
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
    }, [deployed, deployment, timer, extended]);

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
                    outPorts.push("nc " + deployment.host + " " + String(portmap[key]));
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
                <div>
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
                    <div id="description" style={{overflowWrap: "break-word", color: "#f0f0f0", fontSize: "20px"}}>
                        <ReactMarkdown>{description}</ReactMarkdown>
                    </div>
                    <br></br>
                </div>
            </>
        );

        if (deployed && deployment) {
            buttons = (
                <div className="deployment-info">
                    {config.recaptcha_site_key && (
                        <ReCaptcha sitekey={config.recaptcha_site_key} ref={captchaRef} size="invisible" />
                    )}
                    {chall.is_shared ? (
                        <>
                            <button className="deploy ON shared">
                                <Timer className="buttonsvg l" />
                                <span style={{marginLeft: "0", marginRight: "4rem"}}>{prettyTime(timer)}</span>
                            </button>
                        </>
                    ) : (
                        <>
                            <button className="deploy ON" onClick={terminateChallenge} disabled={disableButton[0]}>
                                <Timer className="buttonsvg l" />
                                <span style={{marginLeft: "0"}}>{prettyTime(timer)}</span>
                                <Stop className="buttonsvg r" />
                            </button>
                        </>
                    )}
                    {Date.now() / 1000 > deployment.start_delay ? (
                        <>
                            <button
                                className={"deploy OFF extend" + (isShaking[1] ? " shake-animation" : "")}
                                onClick={() => deployChallenge(1)}
                                disabled={disableButton[1]}
                            >
                                EXTEND CHALLENGE
                            </button>
                            {chall.is_shared && <div className="IP-port-box"> SHARED CHALLENGE </div>}
                            {ports.map((p: string | JSX.Element) => (
                                <div className="IP-port-box" key={p as string}>
                                    {p}
                                </div>
                            ))}
                        </>
                    ) : (
                        <div className="IP-port-box" key="loading">
                            <div className="loading_3_dots">challenge is booting up, please wait...</div>
                        </div>
                    )}
                </div>
            );
        } else {
            buttons = (
                <>
                    <div className="deployment-info">
                        {config.recaptcha_site_key && (
                            <ReCaptcha sitekey={config.recaptcha_site_key} ref={captchaRef} size="invisible" />
                        )}
                        <button
                            className={"deploy OFF" + (isShaking[0] ? " shake-animation" : "")}
                            onClick={() => deployChallenge(0)}
                            disabled={disableButton[0]}
                        >
                            DEPLOY NOW
                        </button>
                    </div>
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
