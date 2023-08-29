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
    start_delay: number;
    port_mappings: Record<string, string | number>;
};

export type MessageType = {
    msg: string;
    status: string;
};

export type ProfileType = {
    username: string | null;
    email: string | null;
    login_url: string;
};

export interface Profile {
    name: string;
}

export type previewSuccessType = {
    status: string;
    team_name: string;
};

export type previewType = MessageType | previewSuccessType;
