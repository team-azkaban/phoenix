import { RouterProvider } from "react-router-dom";

import AskPhoenix from "../features/region/AskPhoenix";
import { router } from "./routes";

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <AskPhoenix />
    </>
  );
}