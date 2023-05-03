import { useState } from 'react'
import axios from "axios";
import logo from './logo.svg';
import './App.css';

function App() {

   // new line start
  const [profileData, setProfileData] = useState(null)

  function getData() {
    axios({
      method: "GET",
      url:"/api/me",
    })
    .then((response) => {
      const res =response.data
      setProfileData(({
        profile_name: res.name}))
    }).catch((error) => {
      if (error.response) {
        console.log(error.response)
        console.log(error.response.status)
        console.log(error.response.headers)
        }
    })}
    //end of new line 

  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>

        {/* new line start*/}
        <p>Test API request</p><button onClick={getData}>Click me</button>
        {profileData && <div>
              <p>Name: {profileData.profile_name}</p>
            </div>
        }
         {/* end of new line */}
      </header>
    </div>
  );
}

export default App;
