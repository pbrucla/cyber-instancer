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
        <a href={output} className="chall-link">
            {output}
        </a>
    );
}

const Chall = () => {
    /* Redirect if not logged in */
    const {accountToken} = useAccountManagement();
    const [searchParams] = useSearchParams();
    const loginToken = searchParams.get("token");
    const navigate = useNavigate();

    const {ID} = useParams() as {ID: string};

    /* Load challenge */
    const [chall, setChall] = useState<ChallengeInfoType | undefined | null>(undefined);
    const [deployment, setDeployment] = useState<DeploymentType | undefined>();
    const [deployed, setDeployed] = useState<boolean>(false);
    const [timer, setTimer] = useState<number>(-100);

    useEffect(() => {
        async function getDeployment() {
            const challengeDeployment: ChallengeDeploymentType = (await (
                await fetch("/api/challenge/" + ID + "/deployment", {
                    headers: {Authorization: `Bearer ${accountToken as string}`},
                })
            ).json()) as ChallengeDeploymentType;
            if (challengeDeployment.status === "ok") {
                console.debug(challengeDeployment);
                setDeployment(challengeDeployment.deployment);
            } else {
                loggedOutRedirect();
            }
        }
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
        } else if (timer <= 0) {
            const getChall = async () => {
                const res = await fetch("/api/challenge/" + ID, {
                    headers: {Authorization: `Bearer ${accountToken}`},
                });
                if (res.status === 404) {
                    setChall(null);
                    console.debug("Challenge not found");
                    return;
                }
                const challenge = (await res.json()) as SingleChallengeType;
                if (challenge.status === "ok") {
                    setChall(challenge.challenge_info);
                    await getDeployment();
                } else {
                    console.debug("Failed to get chall status");
                    loggedOutRedirect();
                }
            };
            getChall().catch((err) => console.error(err));
        }
    }, [navigate, timer, ID, accountToken, loginToken]);

    let challInfo;
    let buttons;

    /* Deploy challenge */
    const [isShaking, setIsShaking] = useState(false);

    async function deployChallenge() {
        setIsShaking(false);
        const challengeDeployment: ChallengeDeploymentType = (await (
            await fetch("/api/challenge/" + ID + "/deploy", {
                headers: {Authorization: `Bearer ${accountToken as string}`},
                method: "POST",
            })
        ).json()) as ChallengeDeploymentType;
        if (challengeDeployment.status === "ok") {
            setDeployment(challengeDeployment.deployment);
        } else {
            console.error("Deployment error");
        }
    }

    useEffect(() => {
        setDeployed(isDeployed(deployment));
    }, [deployment]);

    /* Terminate challenge */
    async function terminateChallenge() {
        const status: MessageType = (await (
            await fetch("/api/challenge/" + ID + "/deployment", {
                headers: {Authorization: `Bearer ${accountToken as string}`},
                method: "DELETE",
            })
        ).json()) as MessageType;
        if (status.status === "ok") {
            console.debug(status.msg);
            setDeployment(undefined);
        } else {
            console.error("error");
            console.error(status);
        }
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

        if (deployed) {
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
                        <button
                            className="deploy ON"
                            onClick={() => {
                                terminateChallenge().catch((err) => console.error(err));
                            }}
                        >
                            <Timer className="buttonsvg l" />
                            <span style={{marginLeft: "0"}}>{prettyTime(timer)}</span>
                            <Stop className="buttonsvg r" />
                        </button>
                    )}
                    {ports.map((p: string | JSX.Element) => (
                        <div className="IP-port-box" key={p as string}>
                            {p}
                        </div>
                    ))}
                </div>
            );
        } else {
            buttons = (
                <button
                    className={"deploy OFF" + (isShaking ? " shake-animation" : "")}
                    onClick={() => {
                        deployChallenge().catch((err) => {
                            console.log(err);
                            setIsShaking(true);
                        });
                    }}
                >
                    DEPLOY NOW
                </button>
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
