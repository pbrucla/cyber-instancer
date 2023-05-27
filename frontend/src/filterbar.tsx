import {useState} from 'react';
import {ReactComponent as FilterBtn} from "./images/filter.svg";
import "./styles/filterbar.css";

/*
export const OpenFilter = () => {
    return (
        );
}
*/
const categories = [
    'crypto', 'web', 'pwn', 'misc',
];
const tags = [
    'demo', 'beginner', 'advanced', 'intermediate', 'la ctf 2023',
]
const status = [
    'all', 'inactive', 'active'
]



const Filterbar = () => {
    const [open, setOpen]= useState(false);
    const toggle = () => { setOpen(!open); };

    const [expandIC, setExpandIC]= useState(false);
    const dropIC = () => { setExpandIC(!expandIC); };
    const [expandEC, setExpandEC]= useState(false);
    const dropEC = () => { setExpandEC(!expandEC); };
    const [expandIT, setExpandIT]= useState(false);
    const dropIT = () => { setExpandIT(!expandIT); };
    const [expandET, setExpandET]= useState(false);
    const dropET = () => { setExpandET(!expandET); };
    const [expandS, setExpandS]= useState(false);
    const dropS = () => { setExpandS(!expandS); };

    const dropdowns = [
        {id: "INCLUDE CATEGORY", data: categories, state: expandIC, click: dropIC},
        {id: "EXCLUDE CATEGORY", data: categories, state: expandEC, click: dropEC},
        {id: "INCLUDE TAG", data: tags, state: expandIT, click: dropIT},
        {id: "EXCLUDE TAG", data: tags, state: expandET, click: dropET},
        {id: "STATUS", data: status, state: expandS, click: dropS},
    ]

    return(
        <div className={open?'sideOpen':'sideClose'}>
            <div>
                <button onClick={toggle} className={open?'hide':'filterbtnClose'}
                ><FilterBtn className="svg" /></button></div> 
            {open && (
                <div>
                    <div className="block">
                        <button onClick={toggle} className="filterbtnOpen"
                        ><FilterBtn className="svg" /></button>
                    </div>

                    <div className="block">
                            <input placeholder="Search name"></input>
                    </div>

                    {dropdowns.map((elm) => {
                        return(
                            <div className="block">
                            <button className={elm.state?"menuOpen":"menuClose"} onClick={elm.click}>{elm.id}</button>
                            {elm.state && (
                                <div className="drop">
                                {elm.data.map((cat, idx) => {
                                    return(
                                        <div className={(idx === elm.data.length -1)?"dropdownLast":"dropdown"}>
                                            <label>
                                                <input type="checkbox"></input>
                                                {cat}
                                            </label>
                                        </div>
                                    )
                                })}
                                </div>
                            )}                            
                        </div>
                        )
                    })}                                    
                </div>                
            )} 
        </div> 
    )
}

export default Filterbar;