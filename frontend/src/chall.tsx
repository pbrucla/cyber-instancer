import "./styles/index.css";
import "./styles/chall.css";
import {useState, useEffect} from "react";
import {useParams} from "react-router-dom";
import {ReactComponent as Timer} from "./images/timer.svg";
import {ReactComponent as Stop} from "./images/stop.svg";
import {ChallengeInfoType, DeploymentType} from "./data/challs.ts";
import {getCategories, getTags, SingleChallengeType, ChallengeDeploymentType, TerminationType} from "./data/challs.ts";
import useAccountManagement from "./data/account";
import {useNavigate} from "react-router-dom";

function prettyTime(time: number) {
    return (
        Math.floor(time / 3600)
            .toString()
            .padStart(2, "0") +
        ":" +
        Math.floor((time % 3600) / 60)
            .toString()
            .padStart(2, "0") +
        ":" +
        (time % 60).toString().padStart(2, "0")
    );
}

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
    const {getAccountToken} = useAccountManagement();
    const navigate = useNavigate();
    useEffect(() => {
        if (getAccountToken() === null) {
            navigate("/login");
        }
    }, [navigate, getAccountToken]);

    const {ID} = useParams() as {ID: string};

    /* Load challenge */
    const [chall, setChall] = useState<ChallengeInfoType | undefined>();
    const [deployment, setDeployment] = useState<DeploymentType | undefined>();
    const [deployed, setDeployed] = useState<boolean>(false);
    const [timer, setTimer] = useState<number>(-1);

    async function getDeployment() {
        const challengeDeployment: ChallengeDeploymentType = (await (
            await fetch("/api/challenge/" + ID + "/deployment", {
                headers: {Authorization: `Bearer ${getAccountToken() as string}`},
            })
        ).json()) as ChallengeDeploymentType;
        if (challengeDeployment.status === "ok") {
            console.log(challengeDeployment);
            setDeployment(challengeDeployment.deployment);
        } else {
            navigate("/login");
        }
    }

    useEffect(() => {
        if (getAccountToken() === null) {
            navigate("/login");
        } else if (timer < 0) {
            const getChall = async () => {
                const challenge: SingleChallengeType = (await (
                    await fetch("/api/challenge/" + ID, {
                        headers: {Authorization: `Bearer ${getAccountToken() as string}`},
                    })
                ).json()) as SingleChallengeType;
                if (challenge.status === "ok") {
                    console.log(challenge);
                    setChall(challenge.challenge_info);
                    await getDeployment();
                } else {
                    navigate("/login");
                }
            };
            getChall().catch((err) => console.log(err));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [navigate, timer, ID]);

    let challInfo;
    let buttons;

    /* Deploy challenge */
    async function deployChallenge() {
        const challengeDeployment: ChallengeDeploymentType = (await (
            await fetch("/api/challenge/" + ID + "/deploy", {
                headers: {Authorization: `Bearer ${getAccountToken() as string}`},
                method: "POST",
            })
        ).json()) as ChallengeDeploymentType;
        if (challengeDeployment.status === "ok") {
            console.log(challengeDeployment);
            setDeployment(challengeDeployment.deployment);
        } else {
            console.log("Deployment error");
        }
    }

    useEffect(() => {
        setDeployed(deployment !== null && deployment !== undefined);
    }, [deployment]);

    /* Terminate challenge */
    async function terminateChallenge() {
        const status: TerminationType = (await (
            await fetch("/api/challenge/" + ID + "/deployment", {
                headers: {Authorization: `Bearer ${getAccountToken() as string}`},
                method: "DELETE",
            })
        ).json()) as TerminationType;
        if (status.status === "ok") {
            console.log(status.msg);
            setDeployment(undefined);
        } else {
            console.log("error");
            console.log(status);
        }
    }

    /* Timer */
    useEffect(() => {
        let interval = 0;

        if (deployed) {
            if (timer === -1 && deployment) {
                setTimer(Math.floor(deployment.expiration - Date.now() / 1000));
            } else {
                interval = setInterval(() => {
                    setTimer((prevTimer) => prevTimer - 1);
                }, 1000);
            }
        } else if (!deployed) {
            clearInterval(interval);
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
                if (key === "app:8080") {
                    outPorts.push(createLink(portmap[key] as string));
                } else {
                    outPorts.push("nc " + deployment.host + " " + (portmap[key] as string));
                }
            });
            console.log(outPorts);
            setPorts(outPorts);
        }
    }, [deployment, deployed]);

    /* Display information */
    if (chall === undefined) {
        challInfo = <h1 style={{color: "#d0d0d0"}}>ERROR: CHALLENGE NOT FOUND</h1>;
    } else {
        const cat = getCategories(chall);
        const title = chall.name.toUpperCase();
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
                                terminateChallenge().catch((err) => console.log(err));
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
                    className="deploy OFF"
                    onClick={() => {
                        deployChallenge().catch((err) => console.log(err));
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
