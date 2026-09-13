export interface Region {
  id: string;
  name: string;
  subtitle: string;
  country: string;
  status: "available" | "coming_soon";
}