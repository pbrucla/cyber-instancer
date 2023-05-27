export type challProp = {
    id: string,
    name: string,
    tags: string[],
    category: string[],
    description: string,
    deployed: boolean
}

export type portObject = {
    ip: string,
    port: string
}

const challData: challProp[] = [
    {
        id: "1",
        name: "checking",
        tags: ["demo", "beginner"],
        category: ["crypto","osint","web"],
        description: "description for chall1",
        deployed: false
    },
    {
        id: "test",
        name: "Test chall",
        tags: ["demo", "beginner"],
        category: ["crypto","web"],
        description: "description for test",
        deployed: false
    },
    {
        id: "test2",
        name: "Test chall 2",
        tags: ["demo", "advanced"],
        category: ["crypto","osint","pwn"],
        description: "description for test2",
        deployed: true
    },
    {
        id: "test3",
        name: "Test chall 3",
        tags: ["demo", "la ctf 2023"],
        category: ["osint","misc"],
        description: "description for test3",
        deployed: false
    },
    {
        id: "test4",
        name: "Test chall 4",
        tags: ["demo", "beginner"],
        category: ["crypto","web"],
        description: "description for test4",
        deployed: false
    },
    {
        id: "test5",
        name: "Test chall 5",
        tags: ["demo", "advanced"],
        category: ["osint","pwn"],
        description: "description for test5",
        deployed: true
    },
    {
        id: "test 6",
        name: "Test chall 6",
        tags: ["demo", "la ctf 2023"],
        category: ["crypto","misc"],
        description: "description for test6",
        deployed: false
    },
];

export default challData;