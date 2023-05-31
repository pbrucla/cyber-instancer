import "./styles/index.css";
import "./styles/challs.css";
import React, {useState, useEffect} from "react";
import {Link, useNavigate} from "react-router-dom";
import {ChallengeType, TagType} from "./data/challs.ts";
import dropdowns from "./data/filter-tags.ts";

import {ReactComponent as FilterBtn} from "./images/filter.svg";
import {ReactComponent as ClearBtn} from "./images/clear.svg";
import useAccountManagement from "./data/account";

type ShowType = {
    challenge: ChallengeType;
    display: boolean;
};

const include = new Set<string>([]);
const exclude = new Set<string>([]);

let userInput = "";

/* sidebar label */
function Title({value}: {value: number}) {
    if (value === 0) {
        return (
            <div className="boolean">
                <span className="dot inc"></span>include
            </div>
        );
    } else if (value === 2) {
        return (
            <div className="boolean">
                <span className="dot exc"></span>exclude
            </div>
        );
    }
    return <div className="hide"></div>;
}

/* card format */
function getCategories(chall: ChallengeType) {
    return chall.challenge_info.tags.filter((tag: TagType) => tag.is_category).map((tag: TagType) => tag.name);
    ("");
}

function getTags(chall: ChallengeType) {
    return chall.challenge_info.tags.filter((tag: TagType) => !tag.is_category).map((tag: TagType) => tag.name);
    ("");
}

function ChallInfo({challProp}: {challProp: ChallengeType}) {
    const categories = getCategories(challProp);
    const otherTags = getTags(challProp);
    const deployed = challProp.deployment;
    return (
        <Link to={"../chall/".concat(challProp.challenge_info.id.toString())}>
            <button className="card">
                <div style={{position: "relative"}}>
                    <span className="cat">
                        {categories.map((cat) => {
                            return <>{cat.concat(" ").toString()}</>;
                        })}
                    </span>
                    <span className="title">{challProp.challenge_info.name.toUpperCase()}</span>
                    <span className="tag">
                        {otherTags.map((tag) => {
                            return <>{"#".concat(tag.replaceAll(" ", "_").concat(" ").toString())}</>;
                        })}
                    </span>
                    <div className={deployed === null ? "stat OFF" : "stat ON"}>
                        {deployed === null ? "inactive" : "active"}
                    </div>
                </div>
            </button>
        </Link>
    );
}

const ChallPage = () => {
    /* Redirect if not logged in */
    const {getAccountToken} = useAccountManagement();
    const navigate = useNavigate();
    useEffect(() => {
        if (getAccountToken() === null) {
            navigate("/login");
        }
    }, [navigate, getAccountToken]);

    /* expand toggles: sidebar, menus */
    const [open, setOpen] = useState(false);
    const toggle = () => {
        setOpen(!open);
    };

    const [expand, setExpand] = useState(Array(5).fill(false));
    const newExpand = expand.slice();
    function drop(i: number) {
        newExpand[i] = !expand[i];
        setExpand(newExpand);
    }

    /* search bar */
    const [keyphrase, setKeyphrase] = useState<string>(userInput);
    function handleInput(keyphrase: string) {
        userInput = keyphrase.toLowerCase();
        setKeyphrase(userInput);
        ApplyFilter();
    }
    function ClearInput() {
        userInput = "";
        setKeyphrase("");
        ApplyFilter();
    }

    /* filter system */

    const [show, setShow] = useState<ShowType[]>([]);
    function handleChange(checked: boolean, inc: boolean, cat: string) {
        if (checked) {
            inc ? include.add(cat) : exclude.add(cat);
        } else {
            inc ? include.delete(cat) : exclude.delete(cat);
        }
        ApplyFilter();
    }

    function checkCheck(included: boolean, category: string) {
        if (included) {
            return include.has(category);
        }
        return exclude.has(category);
    }

    function ApplyFilter() {
        show.forEach((chall) => {
            const categories = getCategories(chall.challenge);
            const tags = getTags(chall.challenge);
            const all = new Set<string>([...categories, ...tags]);
            if (chall.challenge.deployment !== null) {
                all.add("active");
            } else {
                all.add("inactive");
            }

            let i = true;
            let e = false;
            if (include.size !== 0) {
                const overlap = new Set([...include].filter((x) => all.has(x)));
                i = overlap.size !== 0;
            }
            if (exclude.size !== 0) {
                const overlap = new Set([...exclude].filter((x) => all.has(x)));
                e = overlap.size !== 0;
            }

            if (userInput.length !== 0) {
                if (!chall.challenge.challenge_info.name.toLowerCase().includes(userInput)) {
                    chall.display = false;
                } else if (i && !e) {
                    chall.display = true;
                }
                if (!(i && !e)) {
                    chall.display = false;
                }
            } else {
                if (i && !e) {
                    chall.display = true;
                } else {
                    chall.display = false;
                }
            }
        });
        setShow([...show]);
    }

    /* load challenges */
    useEffect(() => {
        if (getAccountToken() === null) {
            navigate("/login");
        } else {
            const getChalls = async () => {
                const challenges = await (
                    await fetch("/api/challenges", {
                        headers: {Authorization: `Bearer ${getAccountToken()}`},
                    })
                ).json();
                if (challenges.status === "ok") {
                    setShow(
                        challenges.challenges.map((chall: ChallengeType) => {
                            return {challenge: chall, display: true};
                        })
                    );
                } else {
                    navigate("/login");
                }
            };
            getChalls();
        }
    }, []);

    /* content */
    return (
        <React.StrictMode>
            {" "}
            <div style={{width: "100%", height: "100%"}}>
                {/*FILTERBAR: begin*/}
                <div className={open ? "sideOpen" : "sideClose"}>
                    <button onClick={toggle} className={open ? "hide" : "filterbtn close"}>
                        <FilterBtn className="svg" />
                    </button>

                    {open && (
                        <div>
                            <div className="block">
                                <button onClick={toggle} className="filterbtn open">
                                    <FilterBtn className="svg" />
                                </button>
                            </div>

                            <div className="search">
                                <input
                                    className="searchbar"
                                    type="text"
                                    placeholder="Search name..."
                                    value={keyphrase}
                                    onChange={(e) => handleInput(e.target.value)}
                                ></input>
                                <button className="searchbtn" onClick={() => ClearInput()}>
                                    <ClearBtn className="svg" />
                                </button>
                            </div>

                            {dropdowns.map((elm) => {
                                const val = elm.value;
                                return (
                                    <div className="block" key={elm.id}>
                                        <Title value={val}></Title>
                                        <button
                                            className={expand[val] ? "menu open" : "menu close"}
                                            onClick={() => {
                                                drop(val);
                                            }}
                                        >
                                            <span className={expand[val] ? "arrow pointS" : "arrow pointE"}></span>
                                            {elm.id}
                                        </button>

                                        {expand[val] && (
                                            <div className="drop">
                                                {elm.data.map((cat, idx) => {
                                                    return (
                                                        <div
                                                            key={val.toString() + cat}
                                                            className={
                                                                idx === elm.data.length - 1
                                                                    ? "dropdown last"
                                                                    : "dropdown"
                                                            }
                                                        >
                                                            <label className="select">
                                                                <input
                                                                    type="checkbox"
                                                                    onChange={(e) =>
                                                                        handleChange(e.target.checked, elm.include, cat)
                                                                    }
                                                                    defaultChecked={checkCheck(elm.include, cat)}
                                                                ></input>
                                                                {cat}
                                                            </label>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
                {/*FILTERBAR: end*/}

                {/*CARDS: begin*/}
                <div className={open ? "cards contract" : "cards full"}>
                    <div>
                        {show.map((chall) => {
                            if (chall.display) {
                                return <ChallInfo challProp={chall.challenge} />;
                            } else {
                                return null;
                            }
                        })}
                    </div>
                </div>
                {/*CARDS: end*/}
            </div>
        </React.StrictMode>
    );
};
export default ChallPage;
