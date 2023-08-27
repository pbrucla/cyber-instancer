export type ClientConfigType = {
    rctf_mode: boolean;
    rctf_url: string | null;
};

const config = JSON.parse(
    document.head.querySelector<HTMLMetaElement>("meta[name=client-conf]")!.content
) as ClientConfigType;

export default config;
