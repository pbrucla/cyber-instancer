import "./styles/index.css";
import "./styles/info-box.css";

const Profile = () => {
    return (
        <>
            <div className="Profile-Register-div">
            <div className="Profile-Register-div-inner">
            <h1 className="Profile-Register-heading"> PROFILE </h1>
            <div className="container">
                <div className="row">
                <div className="column" style={{borderRadius: "5px 0 0 0"}} >USERNAME</div>
                <div className="column" style={{borderRadius: "0 5px 0 0"}}>name</div>
                </div>
                <div className="row">
                <div className="column">REGISTERED EMAIL</div>
                <div className="column">email</div>
                </div>
                <div className="row">
                <div className="column" style={{borderRadius: "0 0 0 5px"}}>LOGIN URL</div>
                <div className="column" style={{borderRadius: "0 0 5px 0"}}>url</div>
                </div>
            </div>
            </div>
            </div>
        </>
    );
};

export default Profile;
