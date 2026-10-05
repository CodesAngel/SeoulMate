export type DataMode = "api" | "mock";

const configuredMode = process.env.NEXT_PUBLIC_DATA_MODE?.trim().toLowerCase();

export const DATA_MODE: DataMode = configuredMode === "mock" ? "mock" : "api";
export const IS_MOCK_MODE = DATA_MODE === "mock";
