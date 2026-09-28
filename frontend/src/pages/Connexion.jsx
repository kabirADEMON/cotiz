import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import AuthLayout from "../components/AuthLayout";
import { Alerte, MotDePasse } from "../components/ui";

export default function Connexion() {
  const { user, connexion } = useAuth();
  const navigate = useNavigate();
  const [telephone, setTelephone] = useState("+229");
  const [password, setPassword] = useState("");
  const [erreur, setErreur] = useState(null);
  const [envoi, setEnvoi] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function soumettre(e) {
    e.preventDefault();
    setEnvoi(true);
    try {
      await connexion(telephone.replace(/\s/g, ""), password);
      navigate("/");
    } catch (err) {
      setErreur(err.message);
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <AuthLayout titre="Connexion" sousTitre="Heureux de vous revoir.">
      <form onSubmit={soumettre}>
        <Alerte message={erreur} />
        <label className="champ">
          <span>Numéro de téléphone</span>
          <input
            type="tel"
            autoComplete="username"
            value={telephone}
            onChange={(e) => setTelephone(e.target.value)}
            required
          />
        </label>
        <label className="champ">
          <span>Mot de passe</span>
          <MotDePasse
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <button className="bouton bouton-large" disabled={envoi}>
          {envoi ? "Connexion…" : "Se connecter"}
        </button>
      </form>
      <p className="auth-bas">
        Pas encore de compte ? <Link to="/inscription">Créer un compte</Link>
      </p>
    </AuthLayout>
  );
}
