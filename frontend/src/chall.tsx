import "./styles/index.css";
import "./styles/chall.css";
import { useParams } from "react-router-dom";

const Chall = () => {
    let { ID } = useParams();
    return (
        <>
        <div className="content-div">
            <h2 style={{color: "#d0d0d0"}}>CATEGORY</h2>
            <h1 style={{color: "white"}}>ID: {ID} CHALENGE NAME</h1>
            <h3 style={{color: "#ff8c4c"}}>tags</h3>
            <p style={{whiteSpace: "pre", color: "white"}}>Description: blah blah blah</p>
            <button className="round-button">DEPLOY NOW</button>
        </div>
        </>
    );
};

export default Chall;
