import "./styles/index.css";
import "./styles/chall.css";
import { useParams } from "react-router-dom";
import challenges from "./data/challs.ts"
import {ReactComponent as Timer} from "./images/timer.svg";
import {ReactComponent as Stop} from "./images/stop.svg";


const Chall = () => {
    const { ID } = useParams() as { ID: string };
    const chall = challenges.find(element => element["id"] == ID);

    let challInfo;
    let buttons;

    if (chall === undefined) {
        challInfo = (
            <h1 style={{color: "#d0d0d0"}}>ERROR: CHALLENGE NOT FOUND</h1>
        );
    }
    else {
        
        const cat = chall["category"];
        const title = chall["name"].toUpperCase();
        const description = chall["description"];
        const tags = chall["tags"];
        let newTags:string[] =[];
        for(let i = 0; i < tags.length; i++) {
            newTags.push("#".concat(tags[i].concat(" ").toString()))
        }

        const deployed = chall["deployed"];

        challInfo = (
            <>
            <h2 style={{color: "#d0d0d0"}}>{ cat }</h2>
            <h1 style={{color: "white"}}>{ title }</h1>
            <h3 style={{color: "#ff8c4c"}}>{ newTags }</h3>
            <p style={{whiteSpace: "pre", color: "white"}}>{ description }</p>
            </>
        );

        if (deployed) {
            buttons = (
                <button className="deploy ON">
                    <Timer className="svg l" />
                    <span style={{marginLeft: "0"}}>time</span>
                    <Stop className="svg r" />
                </button>
            );
        }
        else {
            buttons = <button className="deploy OFF">DEPLOY NOW</button>;
        }
    }


    return  (
        <div className="content-div">
            {challInfo}
            {buttons}
        </div>    
    );
};

export default Chall;
