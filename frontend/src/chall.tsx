import "./styles/index.css";
import "./styles/chall.css";
import {useParams} from "react-router-dom";
import challenges from "./data/challs.ts";
import {ReactComponent as Timer} from "./images/timer.svg";
import {ReactComponent as Stop} from "./images/stop.svg";
import {portObject} from "./data/challs.ts";

const Chall = () => {
    const {ID} = useParams() as {ID: string};
    const chall = challenges.find((element) => element["id"] === ID);

    let challInfo;
    let buttons;

    const ports: portObject[] = [
        {ip: "127.0.0.1", port: "1337"},
        {ip: "192.168.1.1", port: "55555"},
        {ip: "8.8.8.8", port: "40000"},
    ];

    if (chall === undefined) {
        challInfo = <h1 style={{color: "#d0d0d0"}}>ERROR: CHALLENGE NOT FOUND</h1>;
    } else {
        const cat = chall["category"];
        const title = chall["name"].toUpperCase();
        const description = chall["description"];
        const tags = chall["tags"];
        const newCat: string[] = [];
        const newTags: string[] = [];

        for (let i = 0; i < tags.length; i++) {
            newCat.push(cat[i].concat(" ").toString());
            newTags.push("#".concat(tags[i].replaceAll(" ", "_").concat(" ").toString()));
        }

        const deployed = chall["deployed"];

        challInfo = (
            <>
                <div style={{position: "relative", width: "90%"}}>
                    <div style={{overflowWrap:"break-word", color: "#d0d0d0", fontSize: "30px"}}>{newCat}</div><br></br>
                    <div style={{overflowWrap:"break-word", color: "#ffffff", fontSize: "45px", fontWeight: "bold"}}>{title.toUpperCase()}</div><br></br>
                    <div style={{overflowWrap:"break-word", color: "#ff8c4c", fontSize: "30px"}}>{newTags}</div><br></br>
                    <div style={{overflowWrap:"break-word", color: "#f0f0f0", fontSize: "20px"}}>{description}</div><br></br>
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
                    <div style={{display:"flex",flexDirection:"row", flexWrap:"wrap"}}>
                        {ports.map((p: portObject) => (
                            <div className="IP-port-box">
                                {p.ip}:{p.port}
                            </div>
                        ))}
                    </div>  
                </div>
            );
        } else {
            buttons = (
                <button className="deploy OFF" onClick={() => fetchData(ID)}>
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
    const data = await res.json();
    console.log(data);
    return;
};
