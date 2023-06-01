export type ChallengesType = {
    challenges: ChallengeType[];
    status: string;
};

export type SingleChallengeType = {
    challenge_info: ChallengeInfoType;
    status: string;
};

export type ChallengeDeploymentType = {
    deployment: DeploymentType;
    status: string;
};

export type DisplayType = {
    challenge: ChallengeType;
    display: boolean;
};

export type ChallengeType = {
    challenge_info: ChallengeInfoType;
    deployment: DeploymentType;
};

export type ChallengeInfoType = {
    author: string;
    description: string;
    id: string;
    is_shared: boolean;
    name: string;
    tags: TagType[];
};

export type TagType = {
    name: string;
    is_category: boolean;
};

export type DeploymentType = {
    expiration: number;
    host: string;
    port_mappings: Record<string, string | number>;
};

export type ChallPropType = {
    id: string;
    name: string;
    tags: string[];
    category: string[];
    description: string;
    deployed: boolean;
};

export type TerminationType = {
    msg: string;
    status: string;
};

const challData: ChallPropType[] = [
    {
        id: "1",
        name: "checking",
        tags: ["demo", "beginner"],
        category: ["crypto", "osint", "web"],
        description: "description for chall1",
        deployed: false,
    },
    {
        id: "test",
        name: "Test chall",
        tags: ["demo", "beginner"],
        category: ["crypto", "web"],
        description: "description for test",
        deployed: false,
    },
    {
        id: "test2",
        name: "Test chall 2",
        tags: ["demo", "advanced"],
        category: ["crypto", "osint", "pwn"],
        description: "description for test2",
        deployed: true,
    },
    {
        id: "test3",
        name: "Test chall 3",
        tags: ["demo", "la ctf 2023"],
        category: ["osint", "misc"],
        description: "description for test3",
        deployed: false,
    },
    {
        id: "test4",
        name: "Test chall 4",
        tags: ["demo", "beginner"],
        category: ["crypto", "web"],
        description: "description for test4",
        deployed: false,
    },
    {
        id: "test5",
        name: "Test chall 5",
        tags: ["demo", "advanced"],
        category: ["osint", "pwn"],
        description: "description for test5",
        deployed: true,
    },
    {
        id: "test 6",
        name: "Test chall 6",
        tags: ["demo", "la ctf 2023"],
        category: ["crypto", "misc"],
        description: "description for test6",
        deployed: false,
    },
    {
        id: "test 7",
        name: "Test chall 7",
        tags: ["demo", "revrevrev"],
        category: ["rev", "misc"],
        description: "description for test7",
        deployed: false,
    },
];
export default challData;

export function getCategories(chall: ChallengeInfoType) {
    return chall.tags.filter((tag: TagType) => tag.is_category).map((tag: TagType) => tag.name);
}

export function getTags(chall: ChallengeInfoType) {
    return chall.tags.filter((tag: TagType) => !tag.is_category).map((tag: TagType) => tag.name);
}
