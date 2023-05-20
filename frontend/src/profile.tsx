import "./index.css";
import "./profile.css";

const Profile = () => {
    return (
        <>
            <div className="Profile-div">
            <div className="Profile-div-inner">
            <h1 className="Profile-heading"> PROFILE </h1>
            <div className="container">
                <div className="row">
                <div className="column" style={{borderRadius: "5px 0 0 0"}} >USERNAME</div>
                <div className="column" style={{borderRadius: "0 5px 0 0"}}>name</div>
                </div>
                <div className="row">
                <div className="column">REGISTERED EMAIL</div>
                <div className="column">name</div>
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
