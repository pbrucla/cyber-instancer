import {ChallengeInfoType, DeploymentType, TagType} from "./types.ts";

export function prettyTime(time: number) {
    return (
        Math.floor(time / 3600)
            .toString()
            .padStart(2, "0") +
        ":" +
        Math.floor((time % 3600) / 60)
            .toString()
            .padStart(2, "0") +
        ":" +
        (time % 60).toString().padStart(2, "0")
    );
}
export function getCategories(chall: ChallengeInfoType) {
    return chall.tags.filter((tag: TagType) => tag.is_category).map((tag: TagType) => tag.name);
}

export function getTags(chall: ChallengeInfoType) {
    return chall.tags.filter((tag: TagType) => !tag.is_category).map((tag: TagType) => tag.name);
}

export function isDeployed(deployment: DeploymentType | undefined) {
    return (
        deployment !== undefined &&
        deployment !== null &&
        deployment.expiration > Math.floor(Date.now() / 1000) &&
        Object.keys(deployment.port_mappings).length !== 0
    );
}
