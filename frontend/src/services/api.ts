import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

export const getHealth = async () => {
  const response = await api.get("/health");
  return response.data;
};

export default api;