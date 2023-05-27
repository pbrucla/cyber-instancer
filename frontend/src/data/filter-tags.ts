const categories = [
    'crypto', 'web', 'pwn', 'misc',
];
const tags = [
    'demo', 'beginner', 'advanced', 'intermediate', 'la ctf 2023',
]
const status = [
    'active', 'inactive', 
]

export type option = {
    id: string,
    data: string[],
    value: number,
    include:boolean,
}

const dropdowns:option[] = [
    {id: "CATEGORY", data: categories, value: 0, include: true},
    {id: "TAG", data: tags, value: 1, include: true},
    {id: "CATEGORY", data: categories, value: 2, include: false},
    {id: "TAG", data: tags, value: 3, include: false},
    {id: "STATUS", data: status, value: 4, include: false},       
]

export default dropdowns;