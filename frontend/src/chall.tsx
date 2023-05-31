import "./styles/index.css";
import "./styles/chall.css";
import {useParams} from "react-router-dom";
import challenges from "./data/challs.ts";
import {ReactComponent as Timer} from "./images/timer.svg";
import {ReactComponent as Stop} from "./images/stop.svg";
import {PortObject} from "./data/challs.ts";

const Chall = () => {
    const {ID} = useParams() as {ID: string};
    const chall = challenges.find((element) => element["id"] === ID);

    let challInfo;
    let buttons;

    const ports: PortObject[] = [
        {ip: "127.0.0.1", port: "1337"},
        {ip: "192.168.1.1", port: "55555"},
        {ip: "8.8.8.8", port: "40000"},
    ];

    if (chall === undefined) {
        challInfo = <h1 style={{color: "#d0d0d0"}}>ERROR: CHALLENGE NOT FOUND</h1>;
    } else {
        const cat = chall["category"].map((category) => {return category.concat(" ").toString()});
        const title = chall["name"].toUpperCase();
        const description = chall["description"];
        const tags = chall["tags"];
        const newTags: string[] = [];
        for (let i = 0; i < tags.length; i++) {
            newTags.push("#".concat(tags[i].replaceAll(" ", "_").concat(" ").toString()));
        }

        const deployed = chall["deployed"];

        challInfo = (
            <>
                <h2 style={{color: "#d0d0d0"}}>{cat}</h2>
                <h1 style={{color: "white"}}>{title}</h1>
                <h3 style={{color: "#ff8c4c"}}>{newTags}</h3>
                <p style={{whiteSpace: "pre", color: "white"}}>{description}</p>
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
                        void fetchData(ID);
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

const fetchData = async (id: string) => {
    const res = await fetch("/api/challenge/" + id + "/deployment");
    if (res.status !== 200) {
        return;
    }
    const data: unknown = await res.json();
    console.log(data);
    return;
};
