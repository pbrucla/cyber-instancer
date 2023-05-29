import {useState} from "react";
import axios, {AxiosError, AxiosResponse} from "axios";
import "./styles/home.css";
import {Profile} from "./apiTypes";

const Home = () => {
    const [profileName, setProfileName] = useState<string | null>(null);

    function getData() {
        axios({
            method: "GET",
            url: "/api/me",
        })
            .then((response: AxiosResponse<Profile>) => {
                const res = response.data;
                setProfileName(res.name);
            })
            .catch((error: AxiosError) => {
                if (error.response) {
                    console.log(error.response);
                    console.log(error.response.status);
                    console.log(error.response.headers);
                }
            });
    }

    return (
        <>
            <div className="Home">
                <header className="Home-header">
                    <p>now with vite B)</p>

                    <p>Test API request</p>
                    <button onClick={getData}>Click me</button>
                    {profileName && (
                        <div>
                            <p>Name: {profileName}</p>
                        </div>
                    )}
                </header>
            </div>
        </>
    );
};

export default Home;
