import {useState} from "react";
import axios from "axios";
import "./App.css";

const App = () => {
    const [profileName, setProfileName] = useState<string | null>(null);

    function getData() {
        axios({
            method: "GET",
            url: "/api/me",
        })
            .then((response) => {
                const res = response.data;
                setProfileName(res.name);
            })
            .catch((error) => {
                if (error.response) {
                    console.log(error.response);
                    console.log(error.response.status);
                    console.log(error.response.headers);
                }
            });
    }

    return (
        <>
            <div className="App">
                <header className="App-header">
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

export default App;
