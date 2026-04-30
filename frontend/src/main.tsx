import "./i18n";
import ReactDOM from "react-dom/client";

import "antd/dist/reset.css";
import "katex/dist/katex.min.css";

import App from "./App";
import { useAuthStore } from "./stores/authStore";
import "./styles/global.css";
import "./stores/mistakeStore";

useAuthStore.getState().initializeAuth();

ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
