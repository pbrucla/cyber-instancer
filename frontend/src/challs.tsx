import React from "react";
import {Link} from "react-router-dom";
import challenges, { challProp } from "./data/challs.ts"
import "./styles/challs.css";
import {ReactComponent as FilterBtn} from "./images/filter.svg";

function ChallInfo({ category, name, tags, active, path }: challProp) {
    let status="inactive"
    if (active) { status = "active"}
    return (
        <Link to={path}>
        <button className="card">
            <span>{category}</span>
            <span>{name}</span>
            <span>{tags}</span>
            <span>{status}</span>
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
                    category={chall.category}
                    name={chall.name}
                    tags={chall.tags}
                    active={chall.active}
                    path={chall.path}
                    />
                ))}
            </div>         
        </React.StrictMode>
    )
};
export default HomePage;