import "./index.css";
import "./info-box.css";

const Register = () => {
    return (
        <>
            <div className="Profile-Register-div">
            <div className="Profile-Register-div-inner">
            <h1 className="Profile-Register-heading"> REGISTER </h1>
            <div className="container">
                <div className="row">
                <div className="column" style={{borderRadius: "5px 0 0 0"}} >USERNAME</div>
                <div className="column" style={{borderRadius: "0 5px 0 0"}}>name</div>
                </div>
                <div className="row">
                <div className="column" style={{borderRadius: "0 0 0 5px"}}>EMAIL</div>
                <div className="column" style={{borderRadius: "0 0 5px 0"}}>email</div>
                </div>
            </div>
            </div>
            </div>
        </>
    );
};

export default Register;
