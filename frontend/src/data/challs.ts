export type challProp = {
    id: string,
    name: string,
    tags: string[],
    category: string,
    deployed: boolean,
}

const challData: challProp[] = [
    {
        id: "",
        name: "checking",
        tags: ["demo", "beginner"],
        category: "web",
        deployed: false,
    },
    {
        id: "test",
        name: "Test chall",
        tags: ["demo", "beginner"],
        category: "web",
        deployed: false,
    },
    {
        id: "test2",
        name: "Test chall 2",
        tags: ["demo", "advanced"],
        category: "pwn",
        deployed: true,
    },
    {
        id: "test3",
        name: "Test chall 3",
        tags: ["demo", "la ctf 2023"],
        category: "misc",
        deployed: false,
    },
    {
        id: "test4",
        name: "Test chall 4",
        tags: ["demo", "beginner"],
        category: "web",
        deployed: false,
    },
    {
        id: "test5",
        name: "Test chall 5",
        tags: ["demo", "advanced"],
        category: "pwn",
        deployed: true,
    },
    {
        id: "test 6",
        name: "Test chall 6",
        tags: ["demo", "la ctf 2023"],
        category: "misc",
        deployed: false,
    },
];

export default challData;