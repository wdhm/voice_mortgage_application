import "@fontsource/manrope/400.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";
import React from "react";
import ReactDOM from "react-dom/client";
import { CustomerApp } from "./routes/CustomerApp";
import { ServiceApp } from "./routes/ServiceApp";
import "./styles.css";

function App() {
  const path = window.location.pathname.replace(/\/$/, "") || "/customer";
  return path === "/service" ? <ServiceApp /> : <CustomerApp />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);