import "./styles/index.css";
import "./styles/chall.css";
import {useState, useEffect} from "react";
import {useParams} from "react-router-dom";
import {ReactComponent as Timer} from "./images/timer.svg";
import {ReactComponent as Stop} from "./images/stop.svg";
import {ChallengeInfoType, DeploymentType, PortObject} from "./data/challs.ts";
import {getCategories, getTags, SingleChallengeType, ChallengeDeploymentType} from "./data/challs.ts";
import useAccountManagement from "./data/account";
import {useNavigate} from "react-router-dom";

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

    async function getDeployment() {
        const challengeDeployment: ChallengeDeploymentType = await (
            await fetch("/api/challenge/" + ID + "/deployment", {
                headers: {Authorization: `Bearer ${getAccountToken()}`},
            })
        ).json();
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
        } else {
            const getChall = async () => {
                const challenge: SingleChallengeType = await (
                    await fetch("/api/challenge/" + ID, {
                        headers: {Authorization: `Bearer ${getAccountToken()}`},
                    })
                ).json();
                if (challenge.status === "ok") {
                    console.log(challenge);
                    setChall(challenge.challenge_info);
                    await getDeployment();
                } else {
                    navigate("/login");
                }
            };
            getChall();
        }
    }, [navigate]);

    let challInfo;
    let buttons;

    const ports: PortObject[] = [
        {ip: "127.0.0.1", port: "1337"},
        {ip: "192.168.1.1", port: "55555"},
        {ip: "8.8.8.8", port: "40000"},
    ];

    /* Deploy challenge */
    async function deployChallenge() {
        console.log("test");
        const challengeDeployment: ChallengeDeploymentType = await (
            await fetch("/api/challenge/" + ID + "/deployment", {
                headers: {Authorization: `Bearer ${getAccountToken()}`},
                method: "POST",
            })
        ).json();
        if (challengeDeployment.status === "ok") {
            console.log(challengeDeployment);
            setDeployment(challengeDeployment.deployment);
        } else {
            console.log("Deployment error");
        }
    }

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

        const deployed = deployment !== null;

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
                    <button className="deploy ON">
                        <Timer className="buttonsvg l" />
                        <span style={{marginLeft: "0"}}>time</span>
                        <Stop className="buttonsvg r" />
                    </button>
                    {ports.map((p: PortObject) => (
                        <div className="IP-port-box" key={`${p.ip}:${p.port}`}>
                            {p.ip}:{p.port}
                        </div>
                    ))}
                </div>
            );
        } else {
            buttons = (
                <button
                    className="deploy OFF"
                    onClick={() => {
                        deployChallenge();
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
