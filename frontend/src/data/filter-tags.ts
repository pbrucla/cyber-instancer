import challData, {challProp} from "./challs.ts";

const challCat = new Set<string>();
const challTag = new Set<string>();

const getAll = (challData: challProp[]) => {
    challData.forEach((elm) => {
        elm.category.forEach((tag) => challCat.add(tag));
        elm.tags.forEach((tag) => challTag.add(tag));
    });
    return [[...challCat].sort(), [...challTag].sort(), ["active", "inactive"]];
};
const all = getAll(challData);

type option = {
    id: string;
    data: string[];
    value: number;
    include: boolean;
};

const dropdowns: option[] = [
    {id: "CATEGORY", data: all[0], value: 0, include: true},
    {id: "TAG", data: all[1], value: 1, include: true},
    {id: "CATEGORY", data: all[0], value: 2, include: false},
    {id: "TAG", data: all[1], value: 3, include: false},
    {id: "STATUS", data: all[2], value: 4, include: false},
];
export default dropdowns;
