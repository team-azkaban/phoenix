import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

export const getHealth = async () => {
  const response = await api.get("/health");
  return response.data;
};

export const askPhoenix = async (question: string) => {
  const response = await api.post<{ answer: string; region: string }>(
    "/chat",
    { question, region: "dahej" },
  );
  return response.data;
};

export default api;