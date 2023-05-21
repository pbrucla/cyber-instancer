import React from "react";
import {Link} from "react-router-dom";
import challenges, { challProp } from "./data/challs.ts"
import "./styles/challs.css";
import {ReactComponent as FilterBtn} from "./images/filter.svg";

function ChallInfo({ id, name, tags, category, deployed }: challProp) {
    let title = name.toUpperCase();

    let newTags:string[] =[];
    for(let i = 0; i < tags.length; i++) {
        newTags.push("#".concat(tags[i].concat(" ").toString()))
    }

    let status="inactive";
    let statusCSS="stat OFF";

    let path="../chall/".concat(id.toString());

    if (deployed) { status = "active"; statusCSS="stat ON"}
    return (
        <Link to={path}>
        <button className="card">
            <div className="text">
                <span className="cat">{category}</span>
                <span className="title">{title}</span>
                <span className="tag">{newTags}</span>
                <div className={statusCSS}>{status}</div>
            </div>            
        </button>
        </Link>
    );
}

const HomePage = () => {
    return (
        <React.StrictMode>   
            <button className="filter"><FilterBtn className="svg" /></button> 
            <div>
                {challenges.map((chall: challProp) => (
                    <ChallInfo
                    id={chall.id}
                    name={chall.name}
                    tags={chall.tags}
                    category={chall.category}
                    deployed={chall.deployed}                    
                    />
                ))}
            </div>         
        </React.StrictMode>
    )
};
export default HomePage;