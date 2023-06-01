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
