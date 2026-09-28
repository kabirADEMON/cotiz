import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./AuthContext";
import Layout from "./components/Layout";
import { Chargement } from "./components/ui";
import Admin from "./pages/Admin";
import Connexion from "./pages/Connexion";
import CyclePage from "./pages/CyclePage";
import Inscription from "./pages/Inscription";
import MesPaiements from "./pages/MesPaiements";
import MesTontines from "./pages/MesTontines";
import Notifications from "./pages/Notifications";
import RetourPaiement from "./pages/RetourPaiement";
import TontinePage from "./pages/TontinePage";

function Protege({ children }) {
  const { user, chargement } = useAuth();
  if (chargement) return <Chargement />;
  return user ? children : <Navigate to="/connexion" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/connexion" element={<Connexion />} />
      <Route path="/inscription" element={<Inscription />} />
      <Route
        element={
          <Protege>
            <Layout />
          </Protege>
        }
      >
        <Route path="/" element={<MesTontines />} />
        <Route path="/tontines/:id" element={<TontinePage />} />
        <Route path="/cycles/:id" element={<CyclePage />} />
        <Route path="/paiements" element={<MesPaiements />} />
        <Route path="/paiements/:id/retour" element={<RetourPaiement />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
