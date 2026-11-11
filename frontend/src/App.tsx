import { Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import WebLibrary from "@/pages/WebLibrary";
import Editor from "@/pages/Editor";
import Vision from "@/pages/Vision";
import Brands from "@/pages/Brands";
import CompanyMap from "@/pages/CompanyMap";
import Engines from "@/pages/Engines";
import Publicities from "@/pages/Publicities";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/web" element={<WebLibrary />} />
      <Route path="/web/p/:id" element={<Editor />} />
      <Route path="/vision" element={<Vision />} />
      <Route path="/publicites" element={<Publicities />} />
      <Route path="/marques" element={<Brands />} />
      <Route path="/carte" element={<CompanyMap />} />
      <Route path="/moteurs" element={<Engines />} />
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
